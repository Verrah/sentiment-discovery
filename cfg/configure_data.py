import os
import copy
import numpy as np

import sentiment_discovery.data_utils as data_utils

class DataConfig(object):
	def __init__(self, parser):
		super(DataConfig,self).__init__()
		self.parser = parser
	def apply(self, cfg, opt):
		print('configuring data')
		train, valid, test = make_loaders(cfg, opt)
		cfg.train = train
		cfg.valid = valid
		cfg.test = test
		cfg.seq_length = opt.seq_length

def make_loaders(cfg, opt):
	"""makes training/val/test"""
	data_loader_args = {'num_workers': 1, 'shuffle': opt.shuffle, 'batch_size': cfg.batch_size,
					'pin_memory': True, 'transpose': opt.transpose, 'distributed': opt.distributed,
					'rank': opt.rank, 'world_size': opt.world_size, 'wrap_last': not opt.no_wrap}
	data_set_args = {
		'path': opt.train, 'seq_length': opt.seq_length, 'cache': opt.cache,
		'text_key': opt.text_key, 'label_key': opt.label_key, 'lazy': opt.lazy,
		'preprocess': opt.preprocess, 'persist_state': opt.persist_state,
		'batch_size': opt.batch_size, 'delim': opt.delim, 'dataset': 'train',
		'ds_type': opt.data_set_type}
	eval_loader_args = copy.copy(data_loader_args)
	eval_set_args = copy.copy(data_set_args)
	# if optional eval args were set then replace their equivalent values in the arg dict
	if opt.eval_batch_size != 0:
		eval_loader_args['batch_size'] = opt.eval_batch_size
		eval_set_args['batch_size'] = opt.eval_batch_size
	if opt.eval_seq_length != 0:
		eval_set_args['seq_length'] = opt.eval_seq_length
	if opt.eval_text_key != 'None':
		eval_set_args['text_key'] = opt.eval_text_key
	if opt.eval_label_key != 'None':
		eval_set_args['label_key'] = opt.eval_label_key

	train = None
	valid = None
	test = None

	if opt.train != 'None':
		train = data_utils.make_dataset(**data_set_args)

	cfg.split = get_split(cfg, opt)
	if should_split(cfg.split) and train is not None:
		train, valid, test = data_utils.split_ds(train, cfg.split)

	if valid is None and opt.valid != 'None':
		eval_set_args['path'] = opt.valid
		eval_set_args['dataset'] = 'val'
		valid = data_utils.make_dataset(**eval_set_args)
	if test is None and opt.test != 'None':
		eval_set_args['path'] = opt.test
		eval_set_args['dataset'] = 'test'
		test = data_utils.make_dataset(**eval_set_args)

	if train is not None:
		train = data_utils.DataLoader(train, **data_loader_args)
	if opt.eval_batch_size != 0:
		data_loader_args['batch_size'] = opt.eval_batch_size
	if valid is not None:
		valid = data_utils.DataLoader(valid, **eval_loader_args)
	if test is not None:
		test = data_utils.DataLoader(test, **eval_loader_args)
	return train, valid, test

def should_split(split):
	return max(split) != 1.

def get_split(cfg, opt):
	splits = []
	if opt.n_split.find(',') != -1: 
		splits = [float(s) for s in opt.n_split.split(',')]
	elif opt.n_split.find('/') != -1:
		splits = [float(s) for s in opt.n_split.split('/')]
	else:
		splits = [float(opt.n_split)]
	split_total = sum(splits)
	if split_total < 1.:
		splits.append(1-split_total)
	while len(splits) < 3:
		splits.append(0.)
	splits = splits[:3]
	if opt.valid != 'None':
		splits[1] = 0.
	if opt.test != 'None':
		splits[2] = 0.
	return list(np.array(splits)/sum(splits))

def configure_data(parser):
	"""add cmdline flags for configuring datasets"""
	parser.add_argument('-train', default='./data/ptb/ptb.train.txt',
						help="""Text filename for training""")
	parser.add_argument('-valid', default='None',
						help="""Text filename for validation""")
	parser.add_argument('-test', default='None',
						help="""Text filename for testing""")
	parser.add_argument('-seq_length', type=int, default=256,
						help="Maximum sequence length to process (for unsupervised rec)")
	parser.add_argument('-batch_size', type=int, default=128,
						help='Maximum batch size')
	parser.add_argument('-eval_seq_length', type=int, default=0,
						help="Maximum sequence length to process for evaluation datasets")
	parser.add_argument('-eval_batch_size', type=int, default=0,
						help='Maximum batch size for evaluation datasets')
	parser.add_argument('-data_size', type=int, default=256,
						help='input dimension of each timestep of data')
	parser.add_argument('-data_set_type', default='unsupervised',
						help='what type of dataset to pull from. one of [unsupervised,csv,json]')
	parser.add_argument('-transpose', action='store_true',
						help='use transposed sampling instead of default sampler for unshuffled sampling.')
	parser.add_argument('-preprocess', action='store_true',
						help='whether to preprocess a dataset while using it')
	parser.add_argument('-shuffle', action='store_true',
						help='whether to shuffle data loader or not')
	parser.add_argument('-delim', default=',',
						help='delimiter used to parse csv testfiles')
	parser.add_argument('-binarize_sent', action='store_true',
						help='binarize sentiment values to 0 or 1 if they\'re on a different scale')
	parser.add_argument('-n_split', default='1.',
						help='comma-separated list of proportions for training, validation, and test split')
	parser.add_argument('-lazy', action='store_true',
						help='whether to lazy evaluate ONLY the training data set')
	parser.add_argument('-text_key', default='sentence',
						help='key to use to extract text from json/csv')
	parser.add_argument('-label_key', default='label',
						help='key to use to extract labels from json/csv')
	parser.add_argument('-eval_text_key', default='None',
						help='key to use to extract text from json/csv evaluation datasets')
	parser.add_argument('-eval_label_key', default='None',
						help='key to use to extract labels from json/csv evaluation datasets')
	parser.add_argument('-drop_unlabeled', action='store_true',
						help='whether or not to drop unlabeled data from training/validation set')
	parser.add_argument('-no_wrap', action='store_true',
						help='whether to not wrap dataset around on the last sample instead of dropping last or providing a partially complete batch')
	parser.add_argument('-persist_state', type=int, default=0,
						help='0=reset state after every sample,1=reset state after every shard,-1=never reset state')
	parser.add_argument('-cache', action='store_true',
						help='use caching mechanism to pull data ')
	return DataConfig(parser)
