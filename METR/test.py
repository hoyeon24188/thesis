import math
import argparse
import utils
import time
import numpy as np
import tensorflow as tf

"""
args : 넣을 변수를 전역적으로 관리하는 변수입니다. ex) arg.P = 12 
만약 실행시, traffic_file을 변경하고싶다면 띄어쓰기 기준으로 추가해주시면 됩니다.
ex) run test.py --traffic_file=/Users/igyubin/school/GMAN/data/metr-la.h5 --test_ratio=/Users/igyubin/school/GMAN/METR/data/SE(METR).txt
"""
parser = argparse.ArgumentParser()
parser.add_argument('--P', type=int, default=12, help='history steps')
parser.add_argument('--Q', type=int, default=12, help='prediction steps')
parser.add_argument('--train_ratio', type=float, default=0.7, help='training set [default : 0.7]')
parser.add_argument('--val_ratio', type=float, default=0.1, help='validation set [default : 0.1]')
parser.add_argument('--test_ratio', type=float, default=0.2, help='testing set [default : 0.2]')
parser.add_argument('--batch_size', type=int, default=32, help='batch size')
parser.add_argument('--traffic_file', default='C:/Users/ajou/Desktop/Data/metr-la.h5', help='traffic file')  # default를 절대 경로로 수정해주세요
parser.add_argument('--SE_file', default='C:/Users/ajou/GMAN/METR/data/SE(METR).txt', help='spatial emebdding file')  # default를 절대 경로로 수정해주세요
parser.add_argument('--model_file', default='C:/Users/ajou/GMAN/METR/data/Adj(METR).txt', help='pre-trained model')  # 존재하지 않습니다 원래 값: data/GMAN(METR)
parser.add_argument('--log_file', default='C:/Users/ajou/GMAN/METR/data/log(METR)', help='log file')  # METR/data 아래에 logfile이 자동으로 생성됩니다.
args = parser.parse_args()

start = time.time()

log = open(args.log_file, 'w')
utils.log_string(log, str(args)[10: -1])

# load data
utils.log_string(log, 'loading data...')
(trainX, trainTE, trainY, valX, valTE, valY, testX, testTE, testY, SE, mean, std) = utils.loadData(args) # traffic_file을 통해 읽어들임
num_train, num_val, num_test = trainX.shape[0], valX.shape[0], testX.shape[0]
utils.log_string(log, 'trainX: %s\ttrainY: %s' % (trainX.shape, trainY.shape))
utils.log_string(log, 'valX:   %s\t\tvalY:   %s' % (valX.shape, valY.shape))
utils.log_string(log, 'testX:  %s\t\ttestY:  %s' % (testX.shape, testY.shape))
utils.log_string(log, 'data loaded!')

# test model
utils.log_string(log, '**** testing model ****')
utils.log_string(log, 'loading model from %s' % args.model_file)
graph = tf.Graph()
with graph.as_default():
    saver = tf.compat.v1.train.import_meta_graph(args.model_file + '.meta') # .meta를 가진 파일이 존재하지 않습니다
config = tf.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
with tf.Session(graph=graph, config=config) as sess:
    saver.restore(sess, args.model_file)
    parameters = 0
    for variable in tf.compat.v1.trainable_variables():
        parameters += np.product([x.value for x in variable.get_shape()])
    utils.log_string(log, 'trainable parameters: {:,}'.format(parameters))
    pred = graph.get_collection(name='pred')[0]
    utils.log_string(log, 'model restored!')
    utils.log_string(log, 'evaluating...')
    trainPred = []
    num_batch = math.ceil(num_train / args.batch_size)
    for batch_idx in range(num_batch):
        start_idx = batch_idx * args.batch_size
        end_idx = min(num_train, (batch_idx + 1) * args.batch_size)
        feed_dict = {
            'X:0': trainX[start_idx: end_idx],
            'TE:0': trainTE[start_idx: end_idx],
            'is_training:0': False}
        pred_batch = sess.run(pred, feed_dict=feed_dict)
        trainPred.append(pred_batch)
    trainPred = np.concatenate(trainPred, axis=0)
    valPred = []
    num_batch = math.ceil(num_val / args.batch_size)
    for batch_idx in range(num_batch):
        start_idx = batch_idx * args.batch_size
        end_idx = min(num_val, (batch_idx + 1) * args.batch_size)
        feed_dict = {
            'X:0': valX[start_idx: end_idx],
            'TE:0': valTE[start_idx: end_idx],
            'is_training:0': False}
        pred_batch = sess.run(pred, feed_dict=feed_dict)
        valPred.append(pred_batch)
    valPred = np.concatenate(valPred, axis=0)
    testPred = []
    num_batch = math.ceil(num_test / args.batch_size)
    start_test = time.time()
    for batch_idx in range(num_batch):
        start_idx = batch_idx * args.batch_size
        end_idx = min(num_test, (batch_idx + 1) * args.batch_size)
        feed_dict = {
            'X:0': testX[start_idx: end_idx],
            'TE:0': testTE[start_idx: end_idx],
            'is_training:0': False}
        pred_batch = sess.run(pred, feed_dict=feed_dict)
        testPred.append(pred_batch)
    end_test = time.time()
    testPred = np.concatenate(testPred, axis=0)
train_mae, train_rmse, train_mape = utils.metric(trainPred, trainY)
val_mae, val_rmse, val_mape = utils.metric(valPred, valY)
test_mae, test_rmse, test_mape = utils.metric(testPred, testY)
utils.log_string(log, 'testing time: %.1fs' % (end_test - start_test))
utils.log_string(log, '                MAE\t\tRMSE\t\tMAPE')
utils.log_string(log, 'train            %.2f\t\t%.2f\t\t%.2f%%' %
                 (train_mae, train_rmse, train_mape * 100))
utils.log_string(log, 'val              %.2f\t\t%.2f\t\t%.2f%%' %
                 (val_mae, val_rmse, val_mape * 100))
utils.log_string(log, 'test             %.2f\t\t%.2f\t\t%.2f%%' %
                 (test_mae, test_rmse, test_mape * 100))
utils.log_string(log, 'performance in each prediction step')
MAE, RMSE, MAPE = [], [], []
for q in range(args.Q):
    mae, rmse, mape = utils.metric(testPred[:, q], testY[:, q])
    MAE.append(mae)
    RMSE.append(rmse)
    MAPE.append(mape)
    utils.log_string(log, 'step: %02d         %.2f\t\t%.2f\t\t%.2f%%' %
                     (q + 1, mae, rmse, mape * 100))
average_mae = np.mean(MAE)
average_rmse = np.mean(RMSE)
average_mape = np.mean(MAPE)
utils.log_string(
    log, 'average:         %.2f\t\t%.2f\t\t%.2f%%' %
         (average_mae, average_rmse, average_mape * 100))
end = time.time()
utils.log_string(log, 'total time: %.1fmin' % ((end - start) / 60))
log.close()
