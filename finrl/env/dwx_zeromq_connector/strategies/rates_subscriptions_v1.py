#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    rates_subscriptions_v1.py
    
    An example using the Darwinex ZeroMQ Connector for Python 3 and MetaTrader 4  PULL REQUEST
    for v2.0.1 in which a Client modify instrument list configured in the EA to get rate prices.
    
    After receiving ... rates from ... it cancels its feed. At this point it cancels all rate feeds. 
    Then it prints _zmq._Market_Data_DB dictionary and finishes. 
    
    -------------------
    Rates feed:
    -------------------
    Through commmand TRACK_RATES, this client can select multiple INSTRUMENTS (symbol, timeframe).
    For example, to receive rates from instruments INTC(M1) and BAC(H1), this client
    will send this command to the Server, through its PUSH channel:

    "TRACK_RATES;INTC;1;BAC;60"

    Server will answer through the PULL channel with a json response like this:

    {'_action':'TRACK_RATES', '_data': {'instrument_count':2}}

    or if errors, then: 

    {'_action':'TRACK_RATES', '_data': {'_response':'NOT_AVAILABLE'}}

    Once subscribed to this feed, it will receive through the SUB channel, rates in this format:
    "INTC_M1 TIME;OPEN;HIGH;LOW;CLOSE;TICKVOL;SPREAD;REALVOL"
    "BAC_H1 TIME;OPEN;HIGH;LOW;CLOSE;TICKVOL;SPREAD;REALVOL"
        
    --
    
    @author: [raulMrello](https://www.linkedin.com/in/raul-martin-19254530/)
    
"""
#############################################################################
# DWX-ZMQ required imports 
#############################################################################
# Import ZMQ-Strategy from relative path
from finrl.env.dwx_zeromq_connector.strategies.base.DWX_ZMQ_Strategy import DWX_ZMQ_Strategy

from finrl.preprocessing.preprocessors import FeatureEngineer
from finrl.config import config

#################################################################################
from pandas import Timestamp
from datetime import timedelta
import datetime

import os
import pandas as pd
import numpy as np

#############################################################################
# Other required imports
#############################################################################
from threading import Lock
from time import sleep
import csv
import random

###############################


#############################################################################
# Class derived from DWZ_ZMQ_Strategy includes data processor for PULL,SUB data
#############################################################################
class rates_subscriptions(DWX_ZMQ_Strategy):
    def __init__(self, 
                 _name="PRICES_SUBSCRIPTIONS",
                 _instruments=[('INTC_M1', 'INTC', 1), ('BAC_M1', 'BAC', 1)],
                 _delay=0.2,
                 _broker_gmt=-3,
                 _verbose=False):
        
        # call DWX_ZMQ_Strategy constructor and passes itself as data processor for handling
        # received data on PULL and SUB ports 
        super().__init__(_name,
                         [],          # Empty symbol list (not needed for this example)
                         _broker_gmt,
                         [self],      # Registers itself as handler of pull data via self.onPullData()
                         [self],      # Registers itself as handler of sub data via self.onSubData()
                         _verbose)
        
        # This strategy's variables
        self._finished = False
        self._instruments = _instruments
        self._delay = _delay
        self._verbose = _verbose

        self.cnt = -1
        self.p_time= "2000-01-01 00:00"

        self.cols = ["date", "open", "high", "low", "close", "volume", "spread", "real_volume", "tic",
                     "upper_band", "lower_band", "ema", "macd_signal", "macd_hist", "cci", "rsi", "adx", "slow_k", "slow_d"]
        
        self._error = False

        # lock for acquire/release of ZeroMQ connector
        self._lock = Lock()
        
    ##########################################################################    
    def isFinished(self):        
        """ Check if execution finished"""
        return self._finished
        
    ##########################################################################
    def Error(self):        
        """ Check if the execution is wrong"""
        return self._error
        
    ##########################################################################    
    def onPullData(self, data):        
        """
        Callback to process new data received through the PULL port
        """        
        # print responses to request commands
        print('Response from ExpertAdvisor={}'.format(data))
        
    ##########################################################################    
    def onSubData(self, data):        
        """
        Callback to process new data received through the SUB port
        """
        # split data to get topic and message and balance
        _topic, _, _msg = data.split("&")

        """
        print('Data on Topic={} with Message={} and Balance={}'.format(_topic,
                                                                       self._zmq._Market_Data_DB[_topic][self._zmq._timestamp],
                                                                       self._zmq._Balance
                                                                       ))
        """
        if self._zmq._Market_Data_DB[_topic][self._zmq._timestamp][0] != self.p_time:
            f1 = open("./" + config.DATA_SAVE_DIR + "/balance.txt", 'w')
            f1.write(self._zmq._Balance); f1.close()
            self.p_time = self._zmq._Market_Data_DB[_topic][self._zmq._timestamp][0]
            self.data_df = pd.DataFrame(columns=self.cols, dtype=float)

        file = "./" + config.DATA_SAVE_DIR + "/data.csv"
        ohlc, indicator = _msg.split("|")
        
        _time, _open, _high, _low, _close, _tick_vol, _spread, _real_vol = ohlc.split(",")
        upper_band, lower_band, ema, macd_signal, macd_hist, cci, rsi, adx, slow_k, slow_d = indicator.split(";")
        
        _time = pd.to_datetime(_time, format="%Y.%m.%d %H:%M")
        _time = datetime.datetime.strftime(_time, "%Y-%m-%d %H:%M:00")
        _time = datetime.datetime.strptime(_time, "%Y-%m-%d %H:%M:00")

        sleep(self._delay*15)
        self.cnt += 1
        self.data_df.loc[self.cnt, :] = (str(_time), float(_open), float(_high), float(_low), float(_close), int(_tick_vol), int(_spread), int(_real_vol), _topic.split("_")[0], \
                                         float(upper_band), float(lower_band), float(ema), float(macd_signal), float(macd_hist), float(cci), float(rsi), float(adx), float(slow_k), float(slow_d))
        
        f1 = open("./finrl/marketdata/f_time.txt", "r+") 
        f_time = f1.read(); f1.close()

        try:
            if (self.cnt+1) % len(self._instruments) == 0:
                assert len(self.data_df) == len(self._instruments) 
                assert self.data_df.index[0] == 0
                self.cnt = -1
                if f_time != str(_time):
                    self.data_df.drop(["spread", "real_volume"], axis=1, inplace=True)
                    fe = FeatureEngineer(use_technical_indicator=False,
                                         tech_indicator_list=config.TECHNICAL_INDICATORS_LIST,
                                         use_turbulence=False,
                                         user_defined_feature=False)
                    processed = fe.preprocess_data(self.data_df)
                    """
                    np.seterr(divide = 'ignore')
                    processed['log_volume'] = np.where((processed.volume * processed.close) > 0, \
                                                       np.log(processed.volume * processed.close), 0)
                    processed['change'] = (processed.close - processed.open) / processed.close
                    processed['daily_variance'] = (processed.high - processed.low) / processed.close
                    """
                    print(processed)
                    processed.to_csv(file)
                    
                    with open('./finrl/marketdata/f_time.txt', 'w') as f2:
                        f2.write('%s' % str(_time))
                            
                    # finishes (removes all subscriptions)
                    self.stop()
                    
        except AssertionError:
            print("\nreceived data is corrupted!")
            self._error = True
            # finishes (removes all subscriptions)
            self.stop()                
                                
        
    ##########################################################################    
    def run(self):
        """
        Starts price subscriptions
        """        
        self._finished = False

        # Subscribe to all symbols in self._symbols to receive bid,ask prices
        self.__subscribe_to_rate_feeds()

    ##########################################################################    
    def stop(self):
        """
        unsubscribe from all market symbols and exits
        """
        # remove subscriptions and stop symbols price feeding
        try:
            # Acquire lock
            self._lock.acquire()
            self._zmq._DWX_MTX_UNSUBSCRIBE_ALL_MARKETDATA_REQUESTS_()
            print('Unsubscribing from all topics')
          
        finally:
            # Release lock
            self._lock.release()
            sleep(self._delay)
      
        try:
            # Acquire lock
            self._lock.acquire()
            self._zmq._DWX_MTX_SEND_TRACKPRICES_REQUEST_([])        
            print('Removing symbols list')
            sleep(self._delay)
            self._zmq._DWX_MTX_SEND_TRACKRATES_REQUEST_([])
            print('Removing instruments list')

        finally:
            # Release lock
            self._lock.release()
            sleep(self._delay)
        
        self._zmq._DWX_ZMQ_SHUTDOWN_S_()
        self._finished = True
                                                            
    ##########################################################################


    ##########################################################################
    def __subscribe_to_rate_feeds(self):
        """
        Starts the subscription to the self._instruments list setup during construction.
        1) Setup symbols in Expert Advisor through self._zmq._DWX_MTX_SUBSCRIBE_MARKETDATA_
        2) Starts price feeding through self._zmq._DWX_MTX_SEND_TRACKRATES_REQUEST_
        """
        if len(self._instruments) > 0:
            
          # subscribe to all instruments' rate feeds
          for _instrument in self._instruments:
            try:
              # Acquire lock
              self._lock.acquire()
              self._zmq._DWX_MTX_SUBSCRIBE_MARKETDATA_(_instrument[0])
              print('Subscribed to {} rate feed'.format(_instrument))
              
            finally:
              # Release lock
              self._lock.release()        
            sleep(self._delay)

          # configure instruments to receive price feeds
          try:
            # Acquire lock
            self._lock.acquire()
            self._zmq._DWX_MTX_SEND_TRACKRATES_REQUEST_(self._instruments)
            print('Configuring rate feed for {} instruments'.format(len(self._instruments)))
            
          finally:
            # Release lock
            self._lock.release()
            sleep(self._delay)     
