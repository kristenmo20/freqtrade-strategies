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


class KeltnerOptimizedV2(IStrategy):
    timeframe = "1d"
    stoploss = -0.20
    minimal_roi = {
        "0": 0.6759999999999999,
      "9800": 0.39299999999999996,
      "24767": 0.11,
      "29343": 0
    }

    trailing_stop = False
    trailing_only_offset_is_reached = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Hyperopt spaces
    window_range = IntParameter(13, 56, default=16, space="buy")
    atrs_range = IntParameter(1, 8, default=1, space="buy")
    rsi_buy_hline = IntParameter(30, 70, default=61, space="buy")
    macd_buy_hline = DecimalParameter(-5, 5, default=0, space="buy")
    stoch_buy_hline = IntParameter(10, 90, default=30, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Keltner Channel
        for windows in self.window_range.range:
            for atrss in self.atrs_range.range:
                dataframe[f"kc_upperband_{windows}_{atrss}"] = \
                qtpylib.keltner_channel(dataframe, window=windows, atrs=atrss)["upper"]
                dataframe[f"kc_middleband_{windows}_{atrss}"] = \
                qtpylib.keltner_channel(dataframe, window=windows, atrs=atrss)["mid"]

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # Stochastic
        stoch = ta.STOCH(dataframe)
        dataframe["slowk"] = stoch["slowk"]
        dataframe["slowd"] = stoch["slowd"]

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(
            (qtpylib.crossed_above(dataframe['close'],
                                   dataframe[f"kc_upperband_{self.window_range.value}_{self.atrs_range.value}"]))
            & (dataframe['rsi'] > self.rsi_buy_hline.value)
            & (dataframe['macd'] > self.macd_buy_hline.value)
            & (dataframe['slowk'] > self.stoch_buy_hline.value)
            & (dataframe['close'] > dataframe['bb_middleband'])
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
            & (dataframe['macd'] < self.macd_buy_hline.value)
            & (dataframe['slowk'] < self.stoch_buy_hline.value)
            & (dataframe['close'] < dataframe['bb_middleband'])
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'exit_long'] = 1

        return dataframe
