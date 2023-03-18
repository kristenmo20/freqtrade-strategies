# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union

from freqtrade.strategy import (
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib


# These libs are for hyperopt
from functools import reduce


class keltnerhopt(IStrategy):
    timeframe = "1d"
    # Both stoploss and roi are set to 100 to prevent them to give a sell signal.
    stoploss = -0.254
    minimal_roi = {
        "0": 0.696,
        "10216": 0.40800000000000003,
        "26070": 0.143,
        "41881": 0,
    }

    # Hyperopt spaces
    buy_params = {
        "window": IntParameter(13, 56, default=16),
        "atrs": IntParameter(1, 8, default=1),
        "rsi_buy_hline": IntParameter(30, 70, default=61),
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Keltner Channel
        for windows in self.buy_params["window"].range:
            for atrss in self.buy_params["atrs"].range:
                dataframe[f"kc_upperband_{windows}_{atrss}"] = qtpylib.keltner_channel(
                    dataframe, window=windows, atrs=atrss
                )["upper"]
                dataframe[f"kc_middleband_{windows}_{atrss}"] = qtpylib.keltner_channel(
                    dataframe, window=windows, atrs=atrss
                )["mid"]

        # Rsi
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(
            (
                qtpylib.crossed_above(
                    dataframe["close"],
                    dataframe[
                        f"kc_upperband_{self.buy_params['window'].value}_{self.buy_params['atrs'].value}"
                    ],
                )
            )
            & (
                dataframe["rsi"]
                > self.buy_params["rsi_buy_hline"].value
            )
        )

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions), "buy"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(
            qtpylib.crossed_below(
                dataframe["close"],
                dataframe[
                    f"kc_middleband_{self.buy_params['window'].value}_{self.buy_params['atrs'].value}"
                ],
            )
        )

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions), "sell"
        ] = 1

        return dataframe
