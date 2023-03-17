### TODO: Comment with docstrings
### TODO: Calculate returns and the associated unittest






import pandas as pd
from typing import Dict, List, Tuple
import json
from pathlib import Path 
import datetime as dt
import numpy as np

feature_path = Path.cwd()/'investment_predictions'/'features.json'
with open(feature_path, 'r') as f:
    features = json.load(f)

class DataParser:
    """
    This class is built to accept the DataScraper.data_dictionary ditionary, parse the 
    data and create a single DataFrame that represents the data for that company. 

    The dictionary passed as an argument contains data relevant to a single company, and thus
    the returned DataFrame is specific to that single company. The current DataScraper design
    should only be used with "company" as the data_type argument, and thus the only acceptable
    keys in the DataScraper.data_dictionary are 'info', 'metrics', 'ratios', 'is' and, 'price'.
    When parsed, only relevant data is passed back from each of the sub-dictionaries. The
    relevant data is defined in the local features.json file that should be present in the
    same directory as this data_parser.py file. Duplicate features are not retured e.g. 
    self.parse_metrics() does not return features that are already returned from 
    self.parse_ratios().

    """

    def __init__(self, data_dictionary: Dict[str, List]):
        self.data_dictionary = data_dictionary
        self.info = self.parse_info()
        self.ratios = self.parse_ratios()
        self.metrics = self.parse_metrics()
        self.is_ = self.parse_income_statement()
        self.price = self.filter_daily_into_quarters(self.parse_price())
        self.snp_500 = self.filter_daily_into_quarters(self.load_snp_500(), 'S&P500')
        self.filter_dataframes()
        self.calculate_PE_ratios()
        self.final_data = self.combine_dataframes()

    @staticmethod
    def json_to_dataframe(json_data: Dict[str, List]) -> pd.DataFrame:
        return pd.DataFrame(json_data)
    
    def create_df_index(self, df: pd.DataFrame) -> pd.Index:
        ticker = self.info['symbol'][0]
        periods = df.period
        years = df.date.apply(lambda x: x.split('-')[0])
        index = ticker+'-'+periods+'-'+years
        return pd.Index(index)
    
    @staticmethod
    def create_period_start_date_feature(date_string_array) -> List[str]:
        dates = np.array([dt.date(*[int(i) for i in date.split('-')]) for date in date_string_array])
        start_dates = dates - dt.timedelta(91)
        return [str(date) for date in start_dates]
        

    def pasrse_data_dictionary(self):
        pass

    def parse_info(self) -> pd.DataFrame:
        json_data = self.data_dictionary['info']
        cols = ['symbol', 'companyName', 'currency', 'exchange', 'industry', 'sector']
        df_data = self.json_to_dataframe(json_data)
        return df_data[cols]
    
    def parse_ratios(self) -> pd.DataFrame:
        '''Need to create period_start_date column as date-91 days'''
        cols = features['ratios']+['start_date']
        json_data = self.data_dictionary['ratios']
        df_data = self.json_to_dataframe(json_data)
        df_data['start_date'] = self.create_period_start_date_feature(df_data.date)
        df_data.index = self.create_df_index(df_data)
        return df_data[cols]
    
    def parse_metrics(self) -> pd.DataFrame:
        cols = features['metrics']+['start_date']
        json_data = self.data_dictionary['metrics']
        df_data = self.json_to_dataframe(json_data)
        df_data['start_date'] = self.create_period_start_date_feature(df_data.date)
        df_data.index = self.create_df_index(df_data)
        return df_data[cols]

    def parse_income_statement(self) -> pd.DataFrame:
        cols = features['is']+['start_date']
        json_data = self.data_dictionary['is']
        df_data = self.json_to_dataframe(json_data)
        df_data['start_date'] = self.create_period_start_date_feature(df_data.date)
        df_data.index = self.create_df_index(df_data)
        return df_data[cols]

    def parse_price(self) -> pd.DataFrame:
        data = self.data_dictionary['price'][0]
        data['date'] = self.create_date_objects_from_pd_timestamps(data.index)
        return data
    
    def filter_dataframes(self) -> None:
        common_idx = self.ratios.index
        common_idx = common_idx.intersection(self.metrics.index)
        common_idx = common_idx.intersection(self.is_.index)
        common_idx = common_idx.intersection(self.price.index)
        self.ratios = self.ratios.loc[common_idx]
        self.metrics = self.metrics.loc[common_idx]
        self.is_ = self.is_.loc[common_idx]
        self.price = self.price.loc[common_idx]
        self.snp_500 = self.snp_500.loc[common_idx]
        failed_msg = "Dataframe filtering failed"
        assert self.ratios.index.equals(self.metrics.index), failed_msg
        assert self.ratios.index.equals(self.is_.index), failed_msg
        assert self.ratios.index.equals(self.price.index), failed_msg
        assert self.ratios.index.equals(self.snp_500.index), failed_msg

    def load_snp_500(self):
        path = Path.cwd()/\
                'investment_predictions'/'data'/\
                    'snp500_trading_data_1970_to_2023.parquet'
        df =  pd.read_parquet(path)
        df['date'] = self.create_date_objects_from_pd_timestamps(df.index)
        return df

    def filter_daily_into_quarters(self, df: pd.DataFrame, tag: str='stock') -> None:
        start_date_objects = self.create_date_objects_from_strings(self.ratios.start_date)
        end_date_objects = self.create_date_objects_from_strings(self.ratios.date)
        working_index = self.ratios.index

        filtered_data = []
        filtered_index = []
        for start, end, idx in zip(start_date_objects, end_date_objects, working_index):
            try:
                period_price = df[(df.date>=start) & (df.date<end)]
                max_ = max(period_price['High'])
                min_ = min(period_price['Low'])
                close = period_price['Close'].mean()
                filtered_data.append([close, max_, min_])
                filtered_index.append(idx)
            except ValueError:
                continue
        
        new_df = pd.DataFrame(filtered_data, columns=[f'{tag}PriceAverage', 
                                                      f'{tag}PriceHigh', 
                                                      f'{tag}PriceLow'], 
                                                      index=filtered_index)
        return new_df

    @staticmethod
    def create_date_objects_from_strings(date_string_array: np.array) -> np.array:
        return np.array([dt.date(*[int(i) for i in date.split('-')]) for date in date_string_array])

    @staticmethod
    def create_date_objects_from_pd_timestamps(timestamp_array) -> np.array:
        return np.array([dt.date(*[int(i) for i in str(stamp).split()[0].split('-')]) for stamp in timestamp_array])

    def calculate_PE_ratios(self) -> None:
        eps = self.is_.eps
        self.ratios['PE_avg'] = self.price['stockPriceAverage']/(4*eps)
        self.ratios['PE_low'] = self.price['stockPriceLow']/(4*eps)
        self.ratios['PE_high'] = self.price['stockPriceHigh']/(4*eps)

    def combine_dataframes(self) -> pd.DataFrame:
        to_drop = ['date', 'period']
        self.metrics = self.metrics.drop(to_drop, axis=1)
        self.is_ = self.is_.drop(to_drop, axis=1)
        to_join = [self.ratios, self.metrics, self.is_, self.price, self.snp_500]
        return pd.concat(to_join, axis=1)
    
    def calculate_returns(self):
        pass
    
