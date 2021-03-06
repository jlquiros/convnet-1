import numpy as np
import sys
import getopt as opt
from util import *
from math import sqrt, ceil, floor
import os
from gpumodel import IGPUModel
import random as r
import numpy.random as nr
from convnet import ConvNet
from options import *
import pylab as pl
import matplotlib.pyplot as plt
import iutils as iu
class TestConvNetError(Exception):
    pass
class TestConvNet(ConvNet):
    def __init__(self, op, load_dict):
        ConvNet.__init__(self, op, load_dic)
        self.statistics = dict()
        self.temp_data = dict()
    def get_gpus(self):
        self.need_gpu = self.op.get_value('analyze_output') is not None
        self.need_gpu |= self.op.get_value('show_estimation') is not None
        self.need_gpu |= self.op.get_value('save_feature_name') is not None
        self.need_gpu |= self.op.get_value('analyze_feature_name') is not None
        #self.need_gpu |= self.op.get_value('ubd_image_folder') is not None
        if self.need_gpu:
            ConvNet.get_gpus( self )
    def init_data_providers(self):
        class Dummy:
            def advance_batch(self):
                pass
        if self.need_gpu:
            ConvNet.init_data_providers(self)
        else:
            self.train_data_provider = self.test_data_provider = Dummy()
    def import_model(self):
        if self.need_gpu:
            ConvNet.import_model(self)
    def init_model_state(self):
        if self.op.get_value('analyze_output'):
            self.softmax_idx = self.get_layer_idx(self.op.get_value('analyze_output'),check_type='softmax')
        if self.op.get_value('show_estimation'):
            self.joint_idx = self.get_layer_idx(self.op.get_value('show_estimation'),check_type='fc')
        if self.op.get_value('save_feature_name'):
            if self.op.get_value('save_feature_path') is None:
                raise TestConvNetError(' Please Specify the path to save features')
            self.feature_idx = self.get_layer_idx(self.op.get_value('save_feature_name'))
        if self.op.get_value('analyze_feature_name'):
            if self.op.get_value('save_feature_path') is None:
                raise TestConvNetError(' Please Specify the path to save features')
            self.feature_idx = self.get_layer_idx(self.op.get_value('analyze_feature_name'))
            feature_name =  self.op.get_value('analyze_feature_name')
            layer_list = [(9,1),(3,2),(5,1),(3,2), (5,1),(3,2)]
            d = {'conv1':0, 'pool1':1, 'conv2':2,'pool2':3,'conv3':4,\
                 'pool3':5, 'conv3_0':4, 'conv3_1':4, 'conv3_max':4}
            extra_d = {'fc_i2':-1, 'fc_ij2':-2, \
                       'fc_ubd2':-3, 'cnorm1':-4, \
                       'data':-5, 'rnorm2':-5, 'rnorm1':-6}
            if feature_name not in d and feature_name not in extra_d:
                raise TestConvNetError('feature %s is not supported' % feature_name)
            if feature_name in d:
                self.layer_filter_size_list = layer_list[0:d[feature_name]+1]
            ### write feature here 
    def init_model_lib(self):
        if self.need_gpu:
            ConvNet.init_model_lib(self)
    def plot_cost(self):
        raise TestConvNetError(' I haven''t finished this part yet')
    def make_filter_fig(self, filters, filter_start, fignum, _title, num_filters, combine_chans):
        raise TestConvNetError(' I haven''t finished this part yet')
    def plot_filters(self):
        raise TestConvNetError(' I haven''t finished this part yet')
    def plot_prediction(self):
        raise TestConvNetError(' I haven''t finished this part yet')
    def do_write_features(self):
        raise TestConvNetError(' I haven''t finished this part yet')
    def show_prediction(self):
        data = self.get_next_batch(train=False)[2]
        num_classes = self.test_data_provider.get_num_classes()
        num_cases = data[0].shape[1]
        label_names = self.test_data_provider.batch_meta['label_names']
        preds = n.zeros((num_cases, num_classes), dtype=n.single)
        idx = self.op.get_value('label_idx')
        print 'label idx = ' + str( idx )
        data += [preds]
        
        # run the model
        self.libmodel.startFeatureWriter(data, self.softmax_idx)
        self.finish_batch()
        label_preds = preds.argmax(axis=1)
        err_idx = n.where(label_preds != data[idx][0,:])[0]
        print len(err_idx)
        print 'The total error is ' + str(len(err_idx)) + ' out of ' + str( num_cases) \
            + ':' + str( len(err_idx) * 100.0 / num_cases)
        confusion_matrix = n.zeros((num_cases, num_classes), dtype=n.int)
        for i in range( num_cases):
            t,p = data[idx][0,i], label_preds[i]
            confusion_matrix[t][p] += 1
        s = '    \t'
        for i in range( num_classes):
            s = s + label_names[i] + '\t'
        print s
        
        for i in range( num_classes):
            s = label_names[i] + '\t'
            for j in range(num_classes):
                s += str( confusion_matrix[i,j]) + '\t'
            print s
    def save_joints8_estimation(self, all_images, true_pose, est_pose, save_folder):
        import Image
        import Stickmen
        from PIL import ImageDraw
        iu.ensure_dir( save_folder )
        num_data = all_images.shape[-1]
        for i in range( num_data ):
            img = all_images[..., i]
            img = Image.fromarray(img.astype('uint8'))
            draw = ImageDraw.Draw(img)
            tp = true_pose[...,i].reshape((8,2), order='C')
            ep = est_pose[...,i].reshape((8,2),order='C')
            # print tp
            # print ep
            Stickmen.draw_joints8(draw, tp, (255,0,0), dual_color=False,width=2)
            Stickmen.draw_joints8(draw, ep, (0, 255, 0), dual_color=False,width=2)
            img.save(iu.fullfile(save_folder, str(i) + '.png'))
    def save_feature(self):
        """
        Currently, only one layer can be saved
        """
        import scipy.io as sio
        testdp = self.test_data_provider
        num_batches = len(testdp.batch_range)
        print 'There are ' + str(testdp.get_num_batches(self.data_path)) + ' in directory'
        print 'There are ' + str( num_batches ) + ' in range'
        iu.ensure_dir(self.save_feature_path)
        feature_name = self.op.get_value('save_feature_name')
        feature_dim = self.model_state['layers'][self.feature_idx]['outputs']
        for b in range(num_batches):
            epoch, b_num, data = self.get_next_batch(train=False)
            print '   Start writing batch......\t' + str(b_num)
            num_data = data[0].shape[-1]
            data += [n.zeros((num_data, feature_dim), dtype=n.single)]
            save_name = 'batch_feature_' + str(b_num) + '_' + feature_name 
            save_path = iu.fullfile(self.save_feature_path, save_name)
            self.libmodel.startFeatureWriter(data, self.feature_idx)
            self.finish_batch()
            d = dict()
            d['X'] = data[-1].transpose()
            d['batch_num'] = b_num
            d['Y'] = data[1]
            d['Y_other'] = data[2:-1] if len(data) > 3 else []
            print 'The len of data is ' + str(len(data))
            print 'The shape of X is' + str(d['X'].shape)
            print 'The shape of Y is' + str(d['Y'].shape)
            sio.savemat(save_path, d)
            pickle(save_path, d)
    def analyze_feature(self):
        # analyze feature
        import scipy.io as sio
        testdp = self.test_data_provider
        num_batches = len(testdp.batch_range)
        print 'There are ' + str(testdp.get_num_batches(self.data_path)) + ' in directory'
        print 'There are ' + str( num_batches ) + ' in range'
        iu.ensure_dir(self.save_feature_path)
        feature_name = self.op.get_value('analyze_feature_name')
        feature_dim = self.model_state['layers'][self.feature_idx]['outputs']
        feature_channel = self.op.get_value('feature_channel')
        abs_sum_feature = n.zeros([feature_dim, 1], dtype=n.float32)
        print 'Feature dimension = ' + str(feature_dim)
        tot_data = 0
        #np.random.seed(7)
        for b in range(num_batches):
            epoch, b_num, data = self.get_next_batch(train=False)
            print '   Start writing batch......\t' + str(b_num)
            num_data = data[0].shape[-1]
            data += [n.zeros((num_data, feature_dim), dtype=n.single)]
            self.libmodel.startFeatureWriter(data, self.feature_idx)
            self.finish_batch()
            abs_sum_feature += np.abs(data[-1]).sum(axis=0).reshape((-1,1))
            tot_data += num_data
                        
            if self.show_response == 'random': 
                num_to_display = min(16, num_data)  
                perm = np.random.randint(0, num_data, num_to_display)
                plot_data  = self.test_data_provider.get_plottable_data(data[0])[..., perm]/255.0
                s = np.sqrt(feature_dim / feature_channel)
                plot_response = data[-1].transpose().reshape((s,s,feature_channel,num_data),order = 'F')[...,perm]
                self.display_image_response(plot_data, plot_response)
            elif self.save_response ==  'separate':
                
                plot_data = self.test_data_provider.get_plottable_data(data[0])/255.0
                s = np.sqrt(feature_dim / feature_channel)
                plot_respose = data[-1].transpose().reshape((s,s,feature_channel, num_data), order='F')
                self.save_image_respose(plot_data, plot_respose, \
                                        'batch_' + str(b_num) + '_res')
            elif self.save_res_patch in {'all','average', 'allpatchdata'}:
                plot_data = self.test_data_provider.get_plottable_data(data[0])/255.0
                s = np.sqrt(feature_dim / feature_channel)
                plot_respose = data[-1].transpose().reshape((s,s,feature_channel, num_data), order='F')
                self.save_image_res_patch(plot_data, plot_respose, \
                                          'batch_' + str(b_num) + '_res')
            elif self.save_indmap_show == 'all':
                plot_data = self.test_data_provider.get_plottable_data(data[0])/255.0
                
                ndata = plot_data.shape[-1]
                s = np.sqrt(data[-1].shape[-1]/feature_channel)
                ind_maps = data[-1].transpose().reshape((feature_channel,s,s,ndata), order='F')

                self.save_image_indmap(plot_data, ind_maps, \
                                           'batch_' + str(b_num) + '_indmap') 
                
        abs_sum_feature /= (tot_data+ 0.0)
        d = dict()
        save_name = 'batch_analysis_' + feature_name 
        save_path = iu.fullfile(self.save_feature_path, save_name)
        d['abs_sum'] = abs_sum_feature
        pickle(save_path, d)
        self.display_feature(np.abs(abs_sum_feature), feature_channel, isrgb=False)
    def makeindmap(self,indmap,s,backgroud = None):
        """
        Create indmap so that the size of indmap matches the original image
        """
        if s == 1:
            raise TestConvNetError('s should be larger than 1')
        wr,wc = indmap.shape[0],indmap.shape[1]
        stride = 12
        filter_size = 30
        if backgroud is None:
            res = np.zeros((wr*s,wc*s,3),dtype=np.float32)
        else:
            alpha = 0.6
            if backgroud.shape != (wr*s,wc*s,3):
                raise TestConvNetError('Error size of backgroud')
            res = alpha * backgroud.copy()
        for i in range(wr):
            for j in range(wc):
                res[i*stride:i*stride+filter_size,j*stride:j*stride+filter_size]+= (1-alpha)* indmap[i,j]
        m = np.minimum(res,1)
        
        return m
    def makeindmapKDE(self,indmap,s, background):
        """
        create detection map using kernel desity estimation

        Rely on  filter_size,
                 stride
        """
        import ipyml
        from ipyml.probability import pfunc
        sp = background.shape
        res = np.zeros((sp[0], sp[1]),dtype=np.float32)
        wr,wc = indmap.shape[0], indmap.shape[1]
        filter_size = 30
        stride = 12
        cov = np.asarray([[(2.0/filter_size)**2,0],[0,(2.0/filter_size)**2]])
        if 'g' in self.temp_data:
            g = self.temp_data['g']
        else:
            g = pfunc.Gaussian2D((sp[0],sp[1]),cov=cov,invcov=False)
            self.temp_data['g'] = g
        center_r = sp[0]
        center_c = sp[1]
        g = g/g.max()
        for r in range(wr):
            for c in range(wc):
                # calcuate the center of detection window
                rr = (r * stride + r * stride + filter_size-1)/2
                cc = (c * stride + c * stride + filter_size-1)/2
                offset_r = center_r - rr
                offset_c = center_c - cc
                res = res + g[offset_r:offset_r+sp[0],offset_c:offset_c+sp[1]] * indmap[r,c]
        idx = np.argmax(res)
        res = np.tile(res.reshape((res.shape[0],res.shape[1],1)),[1,1,3])
        mr = idx / sp[1]
        mc = idx - mr * sp[1]
        hf = filter_size/2
        box = np.asarray([mc -hf,mr -hf,mc + hf, mr + hf])
        return res/3, box


    def save_image_indmap(self, imgdata, indmap, prename):
        if self.save_feature_path is None:
            raise TestConvNetError('Please specify save-feature-path')
        ndata =  imgdata.shape[-1]
        if self.matched_path is not None:
            matched = unpickle(self.matched_path)
            print 'I will removed % d image' % (ndata - matched.size)  
        else:
            matched = range(ndata)
        import Image
        from PIL import ImageDraw
        iu.ensure_dir( self.save_feature_path)
        print 'Begin to save indmap There are %d in total' % ndata
        sp = imgdata.shape
        if sp[0] != sp[1]:
            raise TestConvNetError('Only square images are supported')
        m = 3 # margin size
        num_parts = indmap.shape[0]
        bigimage = np.zeros((sp[0],sp[0] + (sp[0] + m) * indmap.shape[0], sp[2]),dtype=np.float)
        s = sp[0]/indmap.shape[1]
        logistic = lambda x: 1.0/(1 + np.exp(-x))
        indmap = logistic(indmap)
        dp = self.test_data_provider
        if self.ind_type == 'joint_ind':
            tpose = self.transform_pose_back_to_oriimg_coor(dp, dp.data_dic['joints8'] * dp.img_size, False)
            if len(matched) != tpose.shape[-1]:
                raise TestConvNetError('Sample number of groudth-truth and estimation doesn''t match')
            epose = np.zeros((num_parts, 2, tpose.shape[-1]))
        for i in matched:
            if i < 0:
                continue
            bigimage[:] = 0
            bigimage[:sp[0],:sp[1],:] = imgdata[...,i]
            bbox = np.zeros((4,num_parts),dtype=np.float32)
            for j in range(num_parts):
                # draw margin
                c_start = sp[0] + j * (sp[0] + m)
                bigimage[:sp[1],c_start:c_start+m,1] = 1.0
                bigimage[:sp[1],c_start:c_start+m,2] = 1.0
                t1 = c_start + m
                t2 = c_start + m + sp[0]
                indshow, box = self.makeindmapKDE(indmap[j,:,:,i],s,imgdata[...,i])
                bbox[...,j] = box
                # import imgproc
                # bigimage[:sp[0],t1:t2,:] = imgproc.imgeq(np.minimum(1,indshow/2.0))/255.0
                bigimage[:sp[0],t1:t2,:] = imgdata[...,i]
            saveimg = Image.fromarray(np.require(bigimage * 255, dtype=np.uint8))
            draw = ImageDraw.Draw(saveimg)
            inc = [ 0 if x == 0 else 0 for x in range(num_parts)]
            # clist = iu.getrgbtable(num_parts)
            if self.ind_type == 'joint_ind':
                offset = [(0,0) if x == 0 else (0,0) for x in range(num_parts)]
                clist = [(255,255,255), (0,0, 255), (255,255,0), (255,0,0),\
                         (72,118,255), (255,0,255), (0,191,255),(224,102,255)]
            else:
                offset = [(0,-10) if x == 0 else (0,0) for x in range(num_parts)]
                clist = [(255,255,255), (0,0, 255), (255,0,0),\
                         (72,118,255),  (0,191,255),(255,0,255),(224,102,255)] 	
            for j in range(num_parts):
                c_start = sp[0] + j * (sp[0] + m)
                t1 = c_start + m + offset[j][0]
                t2 = offset[j][1]
                draw.rectangle((bbox[0,j]+t1-inc[j],bbox[1,j]+t2-inc[j],bbox[2,j]+t1+inc[j],bbox[3,j]+t2+inc[j]),outline=clist[j])
                # draw all on the left most image
                t1 = t1 - c_start - m
                if self.ind_type != 'joint_ind':
                    draw.rectangle((bbox[0,j]+t1-inc[j],bbox[1,j]+t2-inc[j],bbox[2,j]+t1+inc[j],bbox[3,j]+t2+inc[j]),outline=clist[j])
                else:
                    cc = ((bbox[0,j] + bbox[2,j])/2,(bbox[1,j] + bbox[3,j])/2)
                    draw.rectangle((cc[0]+t1-3,cc[1]+t2-3,cc[0]+t1+3,cc[1]+t2+3),fill=clist[j])
                    ## epose has the same dimension as i
                    epose[j,:,i] = [cc[0],cc[1]] # 
            savename = prename + '_%d.png' % i 
            saveimg.save(iu.fullfile(self.save_feature_path, savename))
        print self.ind_type
        if self.ind_type == 'joint_ind':
            import  iconvnet_datacvt as icvt
            ## The same as in show_joints8_estimation
            epose = self.transform_pose_back_to_oriimg_coor(dp, epose.reshape((-1, tpose.shape[-1]),order='C'), False)
            e = icvt.calc_PCP_from_joints8( tpose, epose, 0.5, True)

    def save_image_res_patch(self,imgdata,resdata, prename, reorder_channel=True):
        import scipy.io as sio
        if self.save_feature_path is None:
                raise TestConvNetError('Please specipy save-feature-path ')
        ndata = imgdata.shape[-1]
        print 'Begin to save reponse, there are ' + str(ndata) + ' in total'
        #prename = 'net10_24_' + prename
        layer_list = self.layer_filter_size_list
        print '======'
        print 'Using Layer structure ' + str(layer_list)
        print '=======' 
        sp = resdata.shape
        resdata = resdata.reshape((sp[0]*sp[1],sp[2],sp[3]),order='F')
        am = np.argmax(resdata, axis=0)
        MAX_IMAGE_ROW=8
        nrow = (sp[2]-1)/MAX_IMAGE_ROW + 1 + 1
        t = 0
        plt.rcParams['figure.figsize'] = 15, min(nrow * 2, 10)
        bbox = list(iu.back_track_filter_range(layer_list, (0,0,0,0)))
        avgpatches = np.zeros((bbox[2], bbox[3] ,imgdata.shape[2], sp[2]), dtype=np.float32)
        avgc = np.zeros((sp[2]), dtype=np.int32)
        
        box = list(iu.back_track_filter_range(layer_list, (0,0,0,0)))
        tc = imgdata[...,0].shape[2]
        curpatches = np.zeros((box[2],box[3], tc, sp[2]),dtype=np.float32)
        sumpatches = np.zeros( imgdata[...,0].shape )
        indpatches = np.zeros( imgdata[...,0].shape,dtype=np.bool )
        patches = np.zeros( imgdata[...,0].shape )
        clist = range(sp[2])
        saveimgall = True if self.save_res_patch =='all' else False
        savepatchall = True if self.save_res_patch=='allpatchdata' else False
        if savepatchall:
            allpatches = np.zeros((box[2],box[3], tc, sp[2], sp[3]),dtype=np.float32)
        if reorder_channel is True and sp[2] == 16:
            if  self.op.get_value('analyze_feature_name') == 'conv3': 
                clist = [ 9, 2, 8,12,4, 7, 0, 3,\
                        15, 6,14, 5,1,11,10,13]
            else: # conv2
                clist = [15, 2, 0, 5, 8,11, 1, 7,\
                         10,13, 4,12, 6,14, 9, 3]
        if reorder_channel is True and sp[2] == 32:
            if  self.op.get_value('analyze_feature_name') == 'conv3': 
                clist = [22, 23, 6, 7, 29, 8, 19, 16, \
                         30, 25, 21, 27, 9, 11, 3, 24,\
                         2,  4,  10, 12, 20, 0, 1, 14, \
                         5, 13, 15,  21, 17, 26,14,28]
                clist = [0, 11, 24, 5, 22, 3, 13, 16, 31,\
                          18, 14, 21, 12, 26, 8, 9, 25, 17,\
                           6, 27, 20, 29, 19, 4, 10, 15, 2,
                            23, 30, 1, 28, 7] # for network 26, c8k19
            elif  self.op.get_value('analyze_feature_name') == 'conv2': 
                clist = [15, 8, 0, 27, 22, 9, 19, \
                         1, 13, 25, 2, 31, 29, 4, \
                         21, 3, 24, 17, 20, 27, 18,\
                          6, 10, 5, 11, 30, 7, 16, \
                          28, 23, 12, 14] # for network 26
        for i in range(sp[3]):
            sumpatches[:] = 0
            indpatches[:] = False
            curpatches[:] = 0
            for cidx in range(sp[2]):
                channel = clist[cidx]
                patches[:] = 0
                index = am[channel, i]
                c = index / sp[0]
                r = index - c * sp[0]
                bbox = list(iu.back_track_filter_range(layer_list, (r,c,r,c)))
                if bbox[0] > imgdata.shape[0] or bbox[1] > imgdata.shape[1]:
                    #plt.imshow(patches)
                    continue
                bbox[2] = min(bbox[2], imgdata.shape[0])
                bbox[3] = min(bbox[3], imgdata.shape[1])
                
                avgpatches[:bbox[2]-bbox[0],:bbox[3]-bbox[1],:,cidx] += \
					imgdata[ bbox[0]:bbox[2], bbox[1]:bbox[3],:, i]
                avgc[cidx] += 1
                curpatches[:bbox[2]-bbox[0],:bbox[3]-bbox[1],:,cidx] = imgdata[ bbox[0]:bbox[2], bbox[1]:bbox[3],:, i]
                patches[bbox[0]:bbox[2], bbox[1]:bbox[3],:] = imgdata[ bbox[0]:bbox[2], bbox[1]:bbox[3],:, i]
                sumpatches[bbox[0]:bbox[2], bbox[1]:bbox[3],:] += imgdata[ bbox[0]:bbox[2], bbox[1]:bbox[3],:, i]
                indpatches[bbox[0]:bbox[2], bbox[1]:bbox[3],:] = True
                
            coverpatch = np.zeros( imgdata[...,0].shape)
            coverpatch[indpatches] = imgdata[indpatches,i]
            if saveimgall:
                self.Show_img_and_patches(imgdata[...,i], curpatches)
                plt.savefig(iu.fullfile(self.save_feature_path, 'img_' + str(i) + '_backtrack.png'),bbox_inches='tight')
                #plt.savefig(iu.fullfile(self.save_feature_path, prename + '_' + str(i) + '.png'))
            if savepatchall:
                allpatches[...,i] = curpatches
            print '%d saved' % i
        if savepatchall:
            if allpatches.shape[-2] <= 16:
                pickle(iu.fullfile(self.save_feature_path, 'patch_data'), allpatches)
            else:
                for i in range(allpatches.shape[-2]):
                    pickle(iu.fullfile(self.save_feature_path, 'patch_data_map_%d' % i), allpatches[:,:,:,i,:])
                    sio.savemat(iu.fullfile(self.save_feature_path, 'patch_data_map_%d' % i), {'data':allpatches[:,:,:,i,:]})
        self.Show_multi_channel_image(avgpatches, True, avgc)
        plt.savefig(iu.fullfile(self.save_feature_path, prename + '_all_filter_avg_imgeq.png'))
        # self.Show_multi_channel_image(avgpatches, False, avgc)
        # plt.savefig(iu.fullfile(self.save_feature_path, prename + '_all_filter_avg_ori.png'))
        if 'avgpatches' not in self.statistics:
            self.statistics['avgpatches'] = avgpatches
            self.statistics['avgc'] = avgc
        else:
            self.statistics['avgpatches'] += avgpatches
            self.statistics['avgc'] += avgc
        self.Show_multi_channel_image(self.statistics['avgpatches'], 'imgeq', self.statistics['avgc'])
        plt.savefig(iu.fullfile(self.save_feature_path, '_all_to_' + prename + '_all_filter_avg_imgeq.png'), bbox_inches='tight')
        self.Show_multi_channel_image(self.statistics['avgpatches'], 'maptorange', self.statistics['avgc'])
        plt.savefig(iu.fullfile(self.save_feature_path, '_all_to_' + prename + '_all_filter_avg_maptorange.png'), bbox_inches='tight')
        
        pickle(iu.fullfile(self.save_feature_path, 'statistics'), self.statistics) 
    def Show_img_and_patches(self, imgdata, patches):
        """
        """
        
        MAX_IMAGE_ROW = 8
        sp = imgdata.shape
        sp1 = patches.shape
        num_patch = patches.shape[-1]
        nrow = (num_patch - 1)/MAX_IMAGE_ROW + 1
        fr = plt.gca()
        fr.axes.get_xaxis().set_visible(False)
        fr.axes.get_yaxis().set_visible(False)
        mg = 5 # margin
        height = max(imgdata.shape[0], nrow * patches.shape[0])
        width = imgdata.shape[1] + MAX_IMAGE_ROW *(patches.shape[1] + mg)
        
        bigimage = np.zeros((height, width, imgdata.shape[2]),dtype=np.float32)
        ## put imgdata
        
        bigimage[:sp[0],:sp[1],:] = imgdata
        ## put patches data
        per_h = height / nrow
        cur_fig = plt.gcf()
        cur_fig.set_size_inches(min(16,MAX_IMAGE_ROW),min(nrow*1.6, 10))
        for i in range(num_patch):
            r = i / MAX_IMAGE_ROW
            c = i - (r * MAX_IMAGE_ROW)
            dr = r * per_h
            dc = sp[1] + (sp1[1] + mg) * c 
            bigimage[dr:sp1[0] + dr,dc:sp1[1] + dc,:] = patches[...,i]
        plt.imshow(bigimage)
        
    def Show_multi_channel_image(self, allimages, enhance=False, num =None):
        """
        This function will show multi channel image in one draw
        num is the number of images in each channel
        """
        import imgproc
        MAX_IMAGE_ROW = 8
        nchannel = allimages.shape[-1]
        nrow = (nchannel - 1)/MAX_IMAGE_ROW + 1
        cur_fig = plt.gcf()
        cur_fig.set_size_inches(min(16,MAX_IMAGE_ROW*1.6),min(nrow*1.6, 10))
        if enhance == 'imgeq':
            f = lambda(x):imgproc.imgeq(x)/255.0
        elif enhance == 'maptorange':
            f = lambda(x):imgproc.maptorange(x,[0,1])
        else:
            f = lambda x: x
        for channel in range(nchannel):
            plt.subplot(nrow, MAX_IMAGE_ROW, channel + 1)
            fr1 = plt.gca()
            fr1.axes.get_xaxis().set_visible(False)
            fr1.axes.get_yaxis().set_visible(False)
            plt.title('%d' % (channel + 1))
            if num is not None:
                plt.imshow( f(allimages[...,channel]/num[channel])) 
            else:
                plt.imshow( f(allimages[...,channel])) 
        
    def save_image_respose(self, imgdata, resdata, prename):
        if self.save_feature_path is None:
            raise TestConvNetError('Please specipy save-feature-path ')
        ndata = imgdata.shape[-1]
        print 'Begin to save reponse, there are ' + str(ndata) + ' in total'
        MAX_IMAGE_ROW = 8
        plt.rcParams['figure.figsize'] = 15, 10
        for i in range(ndata):
            img = imgdata[...,i]
            res = resdata[...,i]
            n_res = res.shape[-1]
            nrow = (n_res - 1)/MAX_IMAGE_ROW + 1 + 1
            plt.subplot(nrow, MAX_IMAGE_ROW, 1)
            plt.imshow(img)
            sp = (res.shape[0], res.shape[1])
            
            for j in range(1, nrow):
                for k in range(MAX_IMAGE_ROW):
                    idx = j * MAX_IMAGE_ROW + k
                    plt.subplot(nrow, MAX_IMAGE_ROW, idx + 1)
                    plt.imshow(res[..., idx - MAX_IMAGE_ROW].reshape(sp))
            plt.savefig(iu.fullfile(self.save_feature_path, prename + '_' + str(i) + '.png'))
            
        
    def prepare_feature_imgae(self, fimg):
        import imgproc
        channel = fimg.shape[-1]
        if channel == 3:
            return fimg
        else:
            return imgproc.imgeq(np.abs(fimg).sum(axis=-1))
    def display_image_response(self, images, responses):
        # image will be in ... x num_data format
        # responses will be ... x num_data format
        MAX_IMG_ROW = 4
        MAX_ROW = 4
        ndata = min(images.shape[-1], MAX_IMG_ROW * MAX_ROW)
        nrow = (ndata-1)/MAX_IMG_ROW + 1
        pl.subplots(2,2)
        import matplotlib.cm as cm
        for i in range(ndata):
            pl.subplot(nrow, MAX_IMG_ROW*2, i*2 + 1) 
            #pl.subplot(2, 2, 0)
            cur_image = images[..., i]
            cur_resp = responses[..., i]
            pl.imshow(cur_image)
            pl.subplot(nrow, MAX_IMG_ROW * 2, (i * 2) + 2)
            cur_resp =self.prepare_feature_imgae(cur_resp)/255.0 
            
            pl.imshow(cur_resp)
            #pl.imshow(cur_resp, cmap=cm.RdBu_r)
        plt.show()
        
    def display_feature(self, imgdata, channel, isrgb = True):
        import imgproc
        if (imgdata.size % channel) != 0:
            raise TestConvNetError('size of image %d can not divide number of channel %d' % (imgdata.size , channel))
        
        s = np.sqrt(imgdata.size / channel)
        if channel == 3:
            imgdata = imgdata.reshape(s,s,channel, order='F')/255.0
        else:
            #imgdata = (imgdata.reshape(s,s,channel, order='F')).reshape((s,s))
            imgdata = imgdata.reshape(s,s,channel, order='F')
        import matplotlib.cm as cm
        #imgdata = iu.imgproc.imgeq(imgdata)/255.0
        # plt.hist(imgdata.flatten(), 1000)
        # plt.show()
        # return
        if isrgb is True:
            pl.imshow(imgdata)
        else:
            MAX_IMG_ROW = 8
            MAX_ROW = 8
            nrow = (channel - 1) / MAX_IMG_ROW + 1
            print '========'
            for i in range( channel):
                pl.subplot(nrow, MAX_IMG_ROW, i + 1)
                curimg = imgproc.imgeq(imgdata[...,i].reshape((s,s)))
                #curimg = imgdata[...,i].reshape((s,s))
                # pl.imshow(curimg, cmap = cm.Greys_r)
                pl.imshow(curimg)
                
               
        plt.show()
    def save_AHEBuffy_estimation(self,data_dic, est_pose, matched, save_folder):
        """
        This function require all the buffy image in the
        data_dic['imgdir'] folder
        And save the estimation to save_folder
        """
        import iconvnet_datacvt as icvt
        import iread.buffy as ibuffy
        import Image
        import Stickmen
        from PIL import ImageDraw
        iu.ensure_dir(save_folder)
        
        imgdir = data_dic['imgdir']
        s = np.sqrt(data_dic['data'].shape[0]/3)
        for m in matched:
            i = -m -1 if m < 0 else m
            ep = data_dic['ep'][...,i]
            fr = data_dic['fr'][...,i]
            imgpath = ibuffy.GetImagePath(imgdir, ep,fr)
            img = Image.open(imgpath)
            draw = ImageDraw.Draw(img)
            coor = data_dic['annotation'][...,i]
            Stickmen.draw_sticks(draw, coor, (255,0,0))
            ubd = Stickmen.EstDetFromStickmen(coor)
            draw.rectangle(ubd, outline=(255,0,0))
            if m >= 0:
                bbox = data_dic['oribbox'][...,m]
                
                est_coor = icvt.convert_joints8_to_AHEcoor(est_pose[...,m])
                est_coor = ibuffy.TransformPoints(est_coor.reshape((2,-1),order='F').transpose(), bbox,(s-1,s-1,3),inv=True).transpose().reshape((4,6),order='F')
                Stickmen.draw_sticks(draw, est_coor, (0,255,0))
                det = data_dic['oridet'][...,m]
                draw.rectangle([det[0],det[1],det[2],det[3]], outline=(0,255,0))
                import ipyml.geometry as igeo
                Mkrec = lambda det: ((det[0],det[1]), (det[2], det[3]))
                ri = igeo.RectIntersectRect(Mkrec(det), Mkrec(ubd))
                
            img.save(iu.fullfile(save_folder, str(i) + '.jpg'))
    def transform_pose_back_to_oriimg_coor(self, dp, pose_arr, view_as_train):
        # 
        # dp is data_provider
        import iread
        if 'joint_sample_offset' in self.test_data_provider.data_dic and view_as_train:
            njoints = pose_arr.shape[0]/2
            offset = np.tile(dp.data_dic['joint_sample_offset'], [njoints, 1])
            res_pose = pose_arr  + offset
        else:
            res_pose = pose_arr
            if view_as_train:
                if 'matdim' in self.test_data_provider.batch_meta:
                    to_dim = self.test_data_provider.batch_meta['matdim']
                else:
                    to_dim = (128,128)
            else:
                if 'newdim' in self.test_data_provider.batch_meta:
                    to_dim = self.test_data_provider.batch_meta['newdim']
                else:
                    to_dim = (112,112)
        res_pose = iread.buffy.TransformJoints8Data(res_pose, dp.data_dic['oribbox'], (to_dim[0]-1, to_dim[1]-1) , inv=True)
        return res_pose
        
    def show_joints8_estimation(self):
        import iconvnet_datacvt as icvt
        import iread
        from time import time 
        data = self.get_next_batch(train=False)[2]
        num_data = data[0].shape[-1]
        
        ests = n.zeros((num_data, 16), dtype=n.single)
        idx = self.joint_idx
        data += [ests]
        img_size = self.test_data_provider.img_size
        s_time = time()
        self.libmodel.startFeatureWriter(data, idx)
        self.finish_batch()
        print 'It takes %.2f seconds' % (time() - s_time) 
        ests = ests.transpose()
        sqdiff = ((data[1] - ests)**2).sum(axis=0)
        all_sqdiff = sqdiff.sum()
        print 'The normalized sqdiff is ' + str( all_sqdiff)
        print 'The normalized avg sqdiff is' + str( all_sqdiff / num_data)
        true_pose = self.test_data_provider.data_dic['joints8'] * img_size
        #true_pose = data[1] * img_size
        est_pose = ests * img_size
        print len(data)
        #print true_pose[:,1].transpose()
        #print est_pose[:,1].transpose()
        estimation_type = op.get_value('estimation_type')
        data_dic = self.test_data_provider.data_dic
        view_as_train = (self.view_as_train == 1)
        if estimation_type is None:
            ######### 
            # Need to convert it into original image
            tpose = self.transform_pose_back_to_oriimg_coor(self.test_data_provider, true_pose, view_as_train)
            epose = self.transform_pose_back_to_oriimg_coor(self.test_data_provider, est_pose, view_as_train)
            #save estimation in original image
            sd = data_dic.copy()
            sd['est_joints8'] = epose
            keys= sd.keys()
            for k in keys:
                if sd[k] is None:
                    del sd[k]
            #icvt.ut.pickle('/home/itsuper7-exp/Desktop/saved-pose', data_dic)
            import scipy.io as sio
            if self.save_estimation:
                sio.savemat(self.save_estimation, sd)
            e = icvt.calc_PCP_from_joints8( tpose, epose, 0.5, True)
        elif estimation_type == 'AHEBuffy':            
            
            Res_list = iread.buffy.MergeAHEBuffyDetection(est_pose, \
                                                    data_dic['oridet'], \
                                                    data_dic['oribbox'],\
                                                    data_dic['annotation'],\
                                                     data_dic['ep'], \
                                                     data_dic['fr'])
            # points will be transformed to original coor
            # in EvaluatePCPFromMergedResult
            dummy1, matched = iread.buffy.EvaluatePCPFromMergedResult(Res_list, \
                                                    (img_size,img_size,3), \
                                                    verbose=True)
            
        # e1 = icvt.calc_Classification_error_from_joints8(true_pose, est_pose, (img_size, img_size, 0))
        save_folder = op.get_value("save_images")
        if save_folder is not None:
            if estimation_type == 'AHEBuffy':
                # data_dic, est_pose, matched, save_folder):
                pickle(iu.fullfile(save_folder, 'matched'), matched)
                self.save_AHEBuffy_estimation(data_dic, est_pose, matched, save_folder)
            else:
                all_images = self.test_data_provider.get_plottable_data(data[0])   
                self.save_joints8_estimation(all_images, true_pose, est_pose, save_folder)
                del all_images
        show_type = op.get_value("show_images")
        if show_type is None or len(true_pose) < 16:
            return
        num_row = num_col = 4
        show_num = num_row * num_col
        if show_type == 'furthest':
            idx = sorted( range(0, num_data), key = lambda x:sqdiff[x], reverse=True)[0:show_num]
        elif show_type == 'random':
            idx = r.sample( range(0,num_data), show_num)
        else:
            return
        from PIL import ImageDraw
        import Image
        import Stickmen
        data[0] = self.test_data_provider.get_plottable_data(data[0])
        for row in range(num_row):
            for col in range(num_col):
                pl_idx = row * num_col + col
                if (pl_idx >= len(true_pose)):
                    break;
                pl.subplot(num_row, num_col, pl_idx)
                img = data[0][...,idx[pl_idx]]
                img = Image.fromarray(img.astype('uint8'))
                draw = ImageDraw.Draw(img)
                tp = true_pose[..., idx[pl_idx]].reshape((8,2),order='C')
                ep = est_pose[..., idx[pl_idx]].reshape((8,2),order='C')
                s = 1
                Stickmen.draw_joints8(draw, tp, (255,0,0))
                Stickmen.draw_joints8(draw, ep, (0,255,0))
                # for i in range(len(tp)):
                #     draw.ellipse((tp[i,0] - s, tp[i,1]-s, tp[i,0] + s,tp[i,1] + s), fill=(255, 0, 0))
                #     draw.ellipse((ep[i,0] - s, ep[i,1]-s, ep[i,0] + s,ep[i,1] + s), fill=(0, 255,0))
                img = n.asarray(img)
                pl.imshow( img )
        
    def save_cost(self):
        # if self.show_cost not in self.train_outputs[0][0]:
        #     raise TestConvNetError('Cost function %s is not defined' % self.show_cost)
        #cost_idxes = [int(x) for x in self.cost_idx.split(',')]
        d = dict()
        d['train_error'] = self.train_outputs
        d['test_error'] = self.test_outputs
        d['costname']= self.train_outputs[0][0].keys()
        d['numbatches'] = len(self.train_batch_range)
        d['testing_freq'] = self.testing_freq
        pickle(self.save_cost_path, d) # 
        
        # for i in cost_idxes:
        #     train_error = [o[0][self.show_cost][i] for o in self.train_outputs]
        #     test_error = [o[0][self.show_cost][i] for o in self.test_outputs]
        #     d['train_error'] += [np.asarray(train_error).reshape((1,-1))]
        #     d['test_error'] += [np.asarray(test_error).reshape((1,-1))]
        # pickle(self.save_cost_path, d)
        
        # print 'There are %d batches' % numbatches
        # print 'len of train_error is %d' % len(train_errors)
        # print 'len of test_error is %d' % len(test_errors)
        # print 'testing freq is %d' % self.testing_freq
        # t = len(train_errors)/( len(test_errors) + 0.0)
        # print 'len train len test = %f' % t
        
    def save_forward_pass_feature(self):
        """
        forward_pass_feature will be in test mode
        
        """
        import iutils as iu
        import scipy.io as sio
        testdp = self.test_data_provider
        num_batches = len(testdp.batch_range)
        print 'There are ' + str(testdp.get_num_batches(self.data_path)) + ' in directory'
        print 'There are ' + str( num_batches ) + ' in range'
        iu.ensure_dir(self.save_feature_path)
        feature_name = self.op.get_value('save_feature_name')
        feature_dim = self.model_state['layers'][self.feature_idx]['outputs']
        for b in range(num_batches):
            epoch, b_num, data = self.get_next_batch(train=False)
            print '   Start writing batch......\t' + str(b_num)
            num_data = data[0].shape[-1]
            data += [n.zeros((num_data, feature_dim), dtype=n.single)]
            save_name = 'data_batch_' + str(b_num)
            save_path = iu.fullfile(self.save_feature_path, save_name)
            self.libmodel.startFeatureWriter(data, self.feature_idx)
            self.finish_batch()
            d = testdp.data_dic.copy()
            d['feature'] = data[-1].transpose()
            d['joints8'] = d['joints8'] * testdp.img_size
            del d['data']
            print 'The shape of feature is' + str(d['feature'].shape)
            pickle(save_path, d)
            sio.savemat(save_path, d)
    def ubd_detect(self):
        # The layer for ubd is specified by self.analyze_feature_name
        # feature_idx is self.feature_idx
        import iutils as iu
        import iread.hmlpe as hp
        ## check self.ubd_dete
        save_folder = self.save_feature_path
        from time import time
        allfile = iu.getfilelist(self.ubd_image_folder, '.*\.(jpg|png|bmp|jpeg)$')
        self.test_data_provider.keep_dic = True
        hmlpe = hp.HMLPE()
        hmlpe.set_imgdata_info({'steps':(28,28)})
        s = 1.618
        scale_pairlist = [ ((1.0/ (s**k)), (1.0/(s**k))) for k in range(0,5)]
        if self.ubd_fix_input_var == -1:
            self.ubd_fix_input_var = 69.8544558 # The mean scale for training  set
        feature_dim = self.model_state['layers'][self.feature_idx]['outputs']
        for f in allfile:
            imgpath = iu.fullfile(self.ubd_image_folder, f)
            t = time()
            d = hmlpe.generate_sliding_detection_data_from_image(imgpath, scale_pairlist)
            ndata = d['data'].shape[-1]
            det_data = np.require(np.zeros((ndata, 1),dtype=np.single), requirements='C')
            det_data = np.require(np.zeros((ndata, feature_dim),dtype=np.single),requirements='C')
            print 'Take %f sec for generating slidding detection' % (time() - t)
            print 'Start Processing: I got %d windows' % ndata
            self.test_data_provider.set_data_dic(d)
            epoch, b_num, data = self.get_next_batch(train=False)
            if self.ubd_fix_input_var:
                cur_s = np.sqrt(np.sum(data[0] ** 2,axis=0)/data[0].shape[0]).reshape((1,ndata))
                print 'median=%.2f mean=%.2f\n======\n' % (np.median(cur_s), np.mean(cur_s))
                cur_s[cur_s == 0] = 1
                data[0] = (data[0]/cur_s) * self.ubd_fix_input_var

            data += [det_data]
            t = time()
            print 'feature idx = %d' % self.feature_idx
            self.libmodel.startFeatureWriter(data,self.feature_idx)
            self.finish_batch()
            # print det_data[12,200:300]
            #print data[0][20:25,10].transpose()
            #t = (det_data.transpose() - data[0]).flatten()
            #print t[:10]
            #print 'diff = %.6f' % (t.sum()/data[0].shape[0]/data[0].shape[1])
            continue
            print 'Need for %f sec for processing' % (time() - t)

            saved = {'detect_score':det_data.transpose(), \
                     'slide_location':d['slide_location'],\
                     'scale':d['scale'],\
                     'imgpath':imgpath}
            pickle(iu.fullfile(save_folder, f + '.detect'), saved)
            print 'Finish %s ' % f
            
        
    def start(self):
        self.op.print_values()
        if self.analyze_output:
            self.show_prediction()
        if self.show_estimation:
            self.show_joints8_estimation()
        elif self.analyze_feature_name:
            print type(self.ubd_image_folder)
            if self.ubd_image_folder:
                self.ubd_detect()
            else:
                self.analyze_feature() 
        elif self.save_feature_name:
            if self.forward_pass_feature:
                self.save_forward_pass_feature()
            else:
                self.save_feature()
        elif self.save_cost_path:
            self.save_cost()
        plt.show()        
        sys.exit(0)

    @classmethod
    def get_options_parser(cls):
        op = ConvNet.get_options_parser()
        for option in list(op.options):
            if option not in ('gpu', 'load_file', 'train_batch_range', 'test_batch_range', 'data_path', 'minibatch_size', 'layer_params'):
                op.delete_option(option)
        op.add_option("analyze-output", "analyze_output", StringOptionParser, "Show specified objective function")
        op.add_option("label-idx", "label_idx", IntegerOptionParser, "The layer idx, with which the output compare") 
        op.add_option("show-estimation", "show_estimation", StringOptionParser, "Show pose estimation result")
        op.add_option("estimation-type", "estimation_type", StringOptionParser, "Determine What type of estimation to use, joints8(default or AHE)")
        op.add_option("save-estimation", "save_estimation", StringOptionParser, "save the estimation result in .mat")
        op.add_option("show-images", "show_images", StringOptionParser, "Whether to use the estimated images")
        op.add_option("save-images", "save_images", StringOptionParser, "Save the estimated images")
        op.add_option("save-feature-name", 'save_feature_name', StringOptionParser, "Save features in layers specified in save_features")
        op.add_option('forward-pass-feature', 'forward_pass_feature', IntegerOptionParser, "indicate whether to transform feature")
        op.add_option('save-feature-path', 'save_feature_path', StringOptionParser, "save layer feature in 'save_feature_path' ")
        op.add_option('analyze-feature-name', 'analyze_feature_name', StringOptionParser, "The layer name of the feature to be analyzed")
        op.add_option('show-response', 'show_response', StringOptionParser, "Displaying the response of input images, used with analyze-feature-name")
        op.add_option('save-response', 'save_response', StringOptionParser, "Save image response of input images, used with analyze-feature-name")
        op.add_option('save-res-patch', 'save_res_patch', StringOptionParser, "Fine the patches responsbile for high activation")
        op.add_option('save-indmap-show', 'save_indmap_show', StringOptionParser, "Display indicator map alone with original image")
        op.add_option('matched-path', 'matched_path', StringOptionParser, "The file for removing all unmatched result")
        op.add_option('feature-channel', 'feature_channel', IntegerOptionParser, "The channel of features")
        op.add_option('ubd-image-folder', 'ubd_image_folder', StringOptionParser, "The folder with images to be analyzed for upper body detection")
        op.add_option('ubd-fix-input-var', 'ubd_fix_input_var', FloatOptionParser, "scale data so that the np.sum((x - mean)**2) == constant")
        # op.add_option('show-cost', 'show_cost', StringOptionParser, 'Display Costs during training')
        # op.add_option("cost-idx", "cost_idx", StringOptionParser, "Cost function return value index for --show-cost", default='0')
        op.add_option('ind-type', 'ind_type', StringOptionParser, 'Indicating whether this is part or joint indicator')
        op.add_option('save-cost-path', 'save_cost_path', StringOptionParser, 'the path to save costs')
        op.add_option("view-as-train", 'view_as_train', IntegerOptionParser, "When regard evaluted data as training batch") 
        op.options['load_file'].default = None
        
        return op

if __name__ == "__main__":
    try:
        op = TestConvNet.get_options_parser()
        op, load_dic = IGPUModel.parse_options(op)
        model = TestConvNet(op, load_dic)
        model.start()
    except (UnpickleError, TestConvNetError, opt.GetoptError), e:
        print '-----------------'
        print "error"
        print e
        print '           '
