

import tensorflow as tf
import numpy as np
import pandas as pd
import joblib
import datetime

today = datetime.datetime.now()
date_time = today.strftime("%m%d%Y%H%M%S")

timeSteps = 5

# convert series to supervised learning
def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    n_vars = 1 if type(data) is list else data.shape[1]
    df = pd.DataFrame(data)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j + 1, i)) for j in range(n_vars)]
    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' % (j + 1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j + 1, i)) for j in range(n_vars)]
    # put it all together
    agg = pd.concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg




def makePredictions(data):

    #scale values
    scaler_filename = "scaler.pkl"
    scaler = joblib.load(scaler_filename)

    scaled = scaler.transform(data)


    reframed = series_to_supervised(scaled, timeSteps, 1)
    test_X = reframed.values

    #create array to append data on (temp column that will be deleted later)
    returnData = np.subtract(np.zeros((data.shape[0] + 5, 1)), np.ones((data.shape[0] + 5, 1)))

    for i in range(1, 6):

        #load model from files
        newModel = tf.keras.models.load_model('./savedModel%s/my_model'%i)

        test_X = test_X.reshape((test_X.shape[0], 1, test_X.shape[1]))


        # make a prediction
        yhat = newModel.predict(test_X)
        test_X = test_X.reshape((test_X.shape[0], test_X.shape[2]))



        # invert scaling for forecast
        inv_yhat = np.concatenate((yhat, data[5:, 1:]), axis=1)
        inv_yhat = scaler.inverse_transform(inv_yhat)#inverse
        # shape data with 0 padding on each side to match input data
        inv_yhat = np.append(np.subtract(np.zeros(5+i), np.ones(5+i)), inv_yhat[:, 0])
        inv_yhat = np.append(inv_yhat, np.subtract(np.zeros(5-i), np.ones(5-i)))

        inv_yhat = inv_yhat.reshape((inv_yhat.shape[0], 1))

        returnData = np.concatenate((returnData, inv_yhat), axis=1)
    returnData = np.delete(returnData, 0, 1)
    return returnData

def makePredictions5ItemList(data):
    # scale values
    scaler_filename = "scaler.pkl"
    scaler = joblib.load(scaler_filename)

    scaled = scaler.transform(data)

    reframed = series_to_supervised(scaled, timeSteps, 1)
    test_X = reframed.values

    # create array to append data on (temp column that will be deleted later)
    returnData = []

    for i in range(1, 6):
        # load model from files
        newModel = tf.keras.models.load_model('./savedModel%s/my_model' % i)

        test_X = test_X.reshape((test_X.shape[0], 1, test_X.shape[1]))

        # make a prediction
        yhat = newModel.predict(test_X)
        test_X = test_X.reshape((test_X.shape[0], test_X.shape[2]))

        # invert scaling for forecast
        inv_yhat = np.concatenate((yhat, data[5:, 1:]), axis=1)
        inv_yhat = scaler.inverse_transform(inv_yhat)  # inverse

        #save predicted value
        predVal = inv_yhat[0, 0]
        #append predicted value to list
        returnData.append(predVal)

    return returnData

def useWaterData(dict_input):
    #initialize empty array for predictions input
    values = np.empty([6, 7])

    #populate array for predictions input
    for i in range(6):
        values[i, 0] = dict_input[i]['Item']['flow']
        values[i, 1] = dict_input[i]['Item']['twinRain1h']
        values[i, 2] = dict_input[i]['Item']['twinRain3h']
        values[i, 3] = dict_input[i]['Item']['bedRain1h']
        values[i, 4] = dict_input[i]['Item']['bedRain3h']
        values[i, 5] = dict_input[i]['Item']['streetsRain1h']
        values[i, 6] = dict_input[i]['Item']['streetsRain3h']

    #predict using values
    predValuesList = makePredictions5ItemList(values)

    return predValuesList
