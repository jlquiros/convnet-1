# Copyright (c) 2013, Li Sijin (lisijin7@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# 
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from data import *
import numpy.random as nr
import numpy as np
from numpy import random as rd
import iutils as iu
from time import time
import Image
class BasicDataProviderError(Exception):
    pass
def iprod(x):
    res = 1
    for t in x:
        res *=t
    return res
def load_images(imagepath, imgsize, mean_image = None):
    """
    The size of all the image should be the same
    """
    dimX = imgsize[0] * imgsize[1] * imgsize[2]
    ndata = len(imagepath)
    if mean_image is None:
        res = np.zeros((dimX,ndata), dtype=np.single)
    else:
        res = np.tile(-mean_image.reshape((-1,1),order='F'), [1, ndata])
    for i,p in enumerate(imagepath):
        res[...,i] += np.asarray(Image.open(p)).reshape((dimX, 1),order='F')
    return  res
def load_cropped_images(imagepath, imgdim, mean_image, crop_dim, \
                        eigvalue, eigvector, sigma=0.1, test=False ):
    """
    Please note that the size of mean_image is imgsize
    """
    dimX = crop_dim[0] * crop_dim[1] * crop_dim[2]
    ndata = len(imagepath)
    pb = np.sqrt(eigvalue).reshape((1,-1)) * eigvector
    a =  np.dot(pb, rd.randn(3, len(imagepath))) * sigma
    res = np.zeros((dimX,ndata), dtype=np.single)
    nr, nc, dummy = np.floor((np.asarray(imgdim) - np.asarray(crop_dim))/2) + 1
    sr_list = rd.randint(nr, size=ndata) if not test else [nr-1] * ndata
    sc_list = rd.randint(nc, size=ndata) if not test else [nc-1] * ndata
    for i,p in enumerate(imagepath):
        curimg = np.asarray(Image.open(p),order='F') - mean_image
        sr = sr_list[i]
        sc = sc_list[i]
        res[...,i] = curimg[sr:sr+crop_dim[0],sc:sc+crop_dim[1],:].reshape((dimX),order='F') + np.tile(a[...,i].reshape((1,3)), [1, dimX/3]).reshape((dimX),order='F') if not test else curimg[sr:sr+crop_dim[0],sc:sc+crop_dim[1],:].reshape((dimX),order='F')
    return sr_list, sc_list, res
class CroppedImageDataProvider(DataProvider):
    """
    
    """
    def __init__(self, data_dir, image_range, init_epoch=1, init_batchnum=None, dp_params={}, test=False):
        DataProvider.__init__(self, data_dir, range(2), init_epoch, init_batchnum, dp_params, test)
        #crop_boarder will crop 2 * crop_boarder in each dimension
        #padding is similar. It will pad both size, i.e., adding 2x pixels
        self.image_dim = self.batch_meta['image_adjust_dim']
        self.input_image_dim = self.batch_meta['image_sample_dim']
        self.mean_image = self.batch_meta['mean_image']
        self.rgb_eigenvalue = self.batch_meta['rgb_eigenvalue']
        self.rgb_eigenvector = self.batch_meta['rgb_eigenvector']
        self.test = test
        self.image_range = np.asarray(image_range)
        self.num_image = len(image_range)
        self.batch_size = dp_params['batch_size']
        if self.batch_size > self.num_image or self.batch_size <= 0:
            raise BasicDataProviderError('Invaid batch_size %d (num_image=%d)' % (self.batch_size, self.num_image))
        self.num_batch = (self.num_image - 1)/ self.batch_size + 1
        # override batch_range
        self.batch_range = range(self.num_batch)
        self.curr_batchnum = min(max(init_batchnum, 0), self.num_image - 1)
        # override batch_Idx
        self.batch_idx = self.curr_batchnum
        rd.seed(7)
        if test:
            # There is no need to shuffle testing data
            self.shuffled_image_range = self.image_range
        else:
            self.shuffled_image_range = self.image_range[rd.permutation(self.num_image)]
    def get_next_batch(self):
        if self.data_dic is None or len(self.batch_range) > 1:
            self.data_dic = self.get_batch(self.curr_batchnum)
        epoch, batchnum = self.curr_epoch, self.curr_batchnum
        self.advance_batch()
        ndata = self.data_dic['data'].shape[-1]
        alldata = [np.require(self.data_dic['data'].reshape((-1,ndata),order='F'),dtype=np.single, requirements='C')]
        return epoch, batchnum, alldata
    def __add_subbatch(self, batch_num, sub_batchnum, batch_dic):
        raise BasicDataProviderError('Not implemented')
    # _joint_batches use the parant class's method
    def get_batch(self, batch_num):
        """
        batch_num in self.image_range
        """
        dic = dict()
        if self.test:
            # test data doesn't need to circle 
            end_num = min(batch_num + self.batch_size, self.num_image)
            cur_batch_indexes = self.shuffled_image_range[batch_num:end_num]
        else:
            cur_batch_indexes = self.shuffled_image_range[ map(lambda x: x if x < self.num_image else x - self.num_image ,range(batch_num, batch_num + self.batch_size)) ]
        ## record the current batch_indexes
        dic['cur_batch_indexes'] = cur_batch_indexes
        ## Load image data
        imagepaths = map(lambda x:self.images_path[x], cur_batch_indexes)
        offset_r, offset_c, dic['data'] = load_cropped_images(imagepaths, self.image_dim, self.mean_image, self.input_image_dim, self.rgb_eigenvalue, self.rgb_eigenvector, 0.1, self.test)
        self.cur_offset_r = offset_r
        self.cur_offset_c = offset_c
        return dic
    def get_data_dims(self, idx=0):
        return iprod(self.input_image_dim) if idx==0 else 1
    def get_plottable_data(self, imgdata):
        ndata = imgdata.shape[-1]
        dimX = imgdata.shape[0]
        res = imgdata.copy()
        for i in range(ndata):
            sr,sc = self.cur_offset_r[i], self.cur_offset_c[i]
            cur_mean = self.mean_image.reshape(self.image_dim, order='F')
            cur_mean = cur_mean[sr:sr+self.input_image_dim[0], sc:sc+self.input_image_dim[1],:]        
            res[...,i] += cur_mean.reshape((dimX),order='F')
        imgdim = list(self.input_image_dim) + [ndata]
        return res.reshape(imgdim, order='F').transpose((3,0,1,2))/255.0
    def advance_batch(self):
        self.batch_idx = self.get_next_batch_idx()
        if self.batch_idx >= self.num_image:
            self.curr_epoch += 1
            self.batch_idx -= self.num_image
        self.curr_batchnum = self.batch_idx
    def get_next_batch_idx(self):
        return self.batch_idx + self.batch_size
    def get_next_batch_num(self):
        return (self.batch_idx + self.batch_size) % self.num_image
    def get_data_file_name(self, batchnum=None):
        return 'There are no data file here'
    def get_num_classes(self):
        return self.num_classes 
    @staticmethod
    def get_batch_filenames(srcdir):
        raise NoahDataProviderError('Should not use this')
    @staticmethod
    def get_batch_nums(srcdir):
        return -1
    @staticmethod
    def get_num_batches(srcdir):
        return -1
