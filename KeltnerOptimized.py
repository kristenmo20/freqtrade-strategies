# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame  # noqa
from datetime import datetime  # noqa
from typing import Optional, Union  # noqa


# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib

# These libs are for hyperopt
from functools import reduce
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter, IStrategy, IntParameter)


class KeltnerOptimized(IStrategy):
    timeframe = "1d"
    # Both stoploss and roi are set to 100 to prevent them to give a sell signal.
    stoploss = -0.254
    minimal_roi = {
        "0": 0.696,
        "10216": 0.40800000000000003,
        "26070": 0.143,
        "41881": 0
    }

    # Hyperopt spaces
    window_range = IntParameter(13, 56, default=16, space="buy")
    atrs_range = IntParameter(1, 8, default=1, space="buy")
    rsi_buy_hline = IntParameter(30, 70, default=61, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Keltner Channel
        for windows in self.window_range.range:
            for atrss in self.atrs_range.range:
                dataframe[f"kc_upperband_{windows}_{atrss}"] = \
                qtpylib.keltner_channel(dataframe, window=windows, atrs=atrss)["upper"]
                dataframe[f"kc_middleband_{windows}_{atrss}"] = \
                qtpylib.keltner_channel(dataframe, window=windows, atrs=atrss)["mid"]

        # Rsi
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Print stuff for debugging dataframe
        # print(metadata)
        # print(dataframe.tail(20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(
            (qtpylib.crossed_above(dataframe['close'],
                                   dataframe[f"kc_upperband_{self.window_range.value}_{self.atrs_range.value}"]))
            & (dataframe['rsi'] > self.rsi_buy_hline.value)
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(
            (qtpylib.crossed_below(dataframe['close'],
                                   dataframe[f"kc_middleband_{self.window_range.value}_{self.atrs_range.value}"]))
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'exit_long'] = 1

        return dataframe