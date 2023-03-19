import sys
from investment_predictions import DataScraper, DataParser
import unittest
from unittest.mock import Mock, patch
import itertools
from pathlib import Path
import requests
import pandas as pd
import datetime as dt
import json
import numpy as np


sys.path.append("..")

key_path = Path().home() / "desktop" / "FinancialModellingPrep_API.txt"
with open(key_path) as file:
    api_key = file.read()

feature_path = Path.cwd() / "investment_predictions" / "features.json"
with open(feature_path, "r") as f:
    features = json.load(f)


def parser_instance_generator():
    """
    Generator function that yields instances of the DataScraper class for various tickers and periods.

    Yields:
        DataScraper: An instance of the DataScraper class.

    """
    tickers = ["AAPL", "NVDA", "MSFT", "XOM"]
    periods = ["annual", "quarter"]
    data_types = ["company"]
    for ticker, period, data_type in itertools.product(tickers, periods, data_types):
        d = DataScraper(ticker, api_key, period, data_type).data_dictionary
        yield DataParser(d)


class TestDataParser(unittest.TestCase):
    """
    Test case for the DataParser class.
    """
    def test_json_to_dataframe(self):
        """
        Test the json_to_dataframe method of the DataParser class.
        
        The method should return a pandas dataframe from the input json data.
        """
        for instance in parser_instance_generator():
            d = instance.data_dictionary
            for key in ["info", "ratios", "metrics", "is"]:
                data = d.get(key)
                expected = pd.DataFrame(d[key])
                result = instance.json_to_dataframe(d[key])
                self.assertEqual(expected.equals(result), True)

    def test_create_df_index(self):
        """
        Test function for create_df_index method of the TestDataParser class.

        For each instance generated by parser_instance_generator, the method is used to create an index
        from a test DataFrame. The expected result is compared with the actual result. The test passes if
        the two indices are equal.

        Returns:
        None
        """
        for instance in parser_instance_generator():
            instance.info["symbol"][0] = "TEST"
            test_df = pd.DataFrame(
                [["Q1", "2000-01-12"], ["Q4", "1995-11-10"], ["Q3", "2020-07-28"]],
                columns=["period", "date"],
            )
            expected_index = pd.Index(["TEST-Q1-2000", "TEST-Q4-1995", "TEST-Q3-2020"])
            result_index = instance.create_df_index(test_df)
            self.assertEqual(result_index.equals(expected_index), True)

    def test_create_period_start_date_feature(self):
        pass

    def test_parse_info(self):
        """Test the parse_info method"""
        for instance in parser_instance_generator():
            instance.data_dictionary["info"] = [
                {
                    "symbol": "AAPL",
                    "changes": 0.4,
                    "companyName": "Apple Inc.",
                    "currency": "USD",
                    "cik": "0000320193",
                    "isin": "US0378331005",
                    "cusip": "037833100",
                    "exchange": "NASDAQ Global Select",
                    "exchangeShortName": "NASDAQ",
                    "industry": "Consumer Electronics",
                    "sector": "Technology",
                    "country": "US",
                    "isActivelyTrading": True,
                }
            ]
            expected = pd.DataFrame(
                [
                    {
                        "symbol": "AAPL",
                        "companyName": "Apple Inc.",
                        "currency": "USD",
                        "exchange": "NASDAQ Global Select",
                        "industry": "Consumer Electronics",
                        "sector": "Technology",
                    }
                ]
            )
            result = instance.parse_info()
            self.assertEqual(expected.equals(result), True)

    def test_parse_ratios(self):
        """
            Tests the `parse_ratios` method of the `TestDataParser` class.

        The test asserts that the resulting data frame has the expected columns
        and the same length as the original data. This test does not check for
        specific values or data types.

        Args:
            None

        Returns:
            None

        Currently just asserts that the columns and data shapes are correct"""
        for instance in parser_instance_generator():
            result_df = instance.parse_ratios()
            result_cols = result_df.columns.to_list()
            expected_cols = features["ratios"] + ["start_date"]
            self.assertEqual(result_cols, expected_cols)
            self.assertEqual(len(result_df), len(instance.data_dictionary["ratios"]))

    def test_parse_metrics(self):
        """
        Tests that parse_metrics() returns a DataFrame with the expected columns and data shape.

        Loops over instances created by parser_instance_generator() and asserts that the resulting DataFrame 
        from parse_metrics() has the expected columns and length, based on the features['metrics'] list and
        the length of the 'metrics' key in the corresponding instance's data_dictionary, respectively.
       

        Currently just asserts that the columns and data shapes are correct"""
        for instance in parser_instance_generator():
            result_df = instance.parse_metrics()
            result_cols = result_df.columns.to_list()
            expected_cols = features["metrics"] + ["start_date"]
            self.assertEqual(result_cols, expected_cols)
            self.assertEqual(len(result_df), len(instance.data_dictionary["metrics"]))

    def test_parse_income_statement(self):
        """
        Asserts that the columns and data shapes are correct for income statement data.

        For each instance of the TestDataParser class generated by the parser_instance_generator function,
        this function tests that the resulting DataFrame from the parse_income_statement method has the
        expected columns and length.

        Currently just asserts that the columns and data shapes are correct

        Returns:
            None
        """
        for instance in parser_instance_generator():
            result_df = instance.parse_income_statement()
            result_cols = result_df.columns.to_list()
            expected_cols = features["is"] + ["start_date"]
            self.assertEqual(result_cols, expected_cols)
            self.assertEqual(len(result_df), len(instance.data_dictionary["is"]))

    def test_parse_price(self):
        """
        Test whether the parse_price method of the TestDataParser class produces the expected DataFrame.

        This method tests that the DataFrame produced by parse_price has the expected columns and a length
        greater than 84. It does not test the content of the DataFrame.

        Currently just asserts that the columns and data shapes are correct

        Returns:
            None
        """
        for instance in parser_instance_generator():
            df = instance.parse_price()
            expected_cols = [
                "Open",
                "High",
                "Low",
                "Close",
                "Adj Close",
                "Volume",
                "date",
            ]
            result_cols = df.columns.to_list()
            self.assertEqual(result_cols, expected_cols)
            self.assertGreater(len(df), 84)

    def test_filter_dataframes(self):
        """Tests the filtering of dataframes.

        Iterates through all Parser instances and tests whether the dataframes are correctly filtered.
        Asserts that the filtered dataframes have the correct indices, column names, and contents.
        Finally, it tests whether an AssertionError is raised when expected and actual results do not match.

        Raises:
            AssertionError: When expected and actual results do not match.
        """
        for instance in parser_instance_generator():
            # Setting the dataframes to predetermined values
            instance.ratios = pd.DataFrame(
                {"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]}
            )
            instance.ratios.index = pd.Index(["X", "Y", "Z"])
            instance.metrics = pd.DataFrame(
                {"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]}
            )
            instance.metrics.index = pd.Index(["J", "Z", "N"])
            instance.is_ = pd.DataFrame(
                {"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]}
            )
            instance.is_.index = pd.Index(["Z", "G", "F"])
            instance.price = pd.DataFrame(
                {"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]}
            )
            instance.price.index = pd.Index(["Z", "v", "w"])
            instance.snp_500 = pd.DataFrame(
                {"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]}
            )
            instance.snp_500.index = pd.Index(["Z", "v", "w"])

            # The expected dataframes after filering are as follows
            expected_ratios = pd.DataFrame({"A": 3, "B": 6, "C": 9}, index=["Z"])
            expected_metrics = pd.DataFrame({"A": 2, "B": 5, "C": 8}, index=["Z"])
            expected_is_ = pd.DataFrame({"A": 1, "B": 4, "C": 7}, index=["Z"])
            expected_price = pd.DataFrame({"A": 1, "B": 4, "C": 7}, index=["Z"])
            expected_snp = pd.DataFrame({"A": 1, "B": 4, "C": 7}, index=["Z"])

            # Filter, then check to assert True
            instance.filter_dataframes()
            self.assertEqual(expected_ratios.equals(instance.ratios), True)
            self.assertEqual(expected_metrics.equals(instance.metrics), True)
            self.assertEqual(expected_is_.equals(instance.is_), True)
            self.assertEqual(expected_price.equals(instance.price), True)
            self.assertEqual(expected_snp.equals(instance.snp_500), True)

            # And finally force an error
            instance.snp_500 = pd.DataFrame(
                {"A": [1, 2, 6], "B": [4, 0, 6], "C": [7, 8, 9]}
            )
            instance.snp_500.index = pd.Index(["a", "b", "c"])
            with self.assertRaises(AssertionError):
                self.assertEqual(expected_snp.equals(instance.snp_500), True)

    def test_load_snp_500(self):
        """Asserts that the loaded S&P 500 data matches the expected data.

        The expected data is loaded from a parquet file, and the test compares this to the
        result of calling the `load_snp_500` method on each parser instance.

        Args:
            None

        Returns:
            None
        """
        path = (
            Path.cwd()
            / "investment_predictions"
            / "data"
            / "snp500_trading_data_1970_to_2023.parquet"
        )

        # expected['date'] = instance.create_date_objects_from_pd_timestamps(df.index)
        for instance in parser_instance_generator():
            expected = pd.read_parquet(path)
            result = instance.load_snp_500().drop("date", axis=1)
            self.assertEqual(result.equals(expected), True)

    def test_filter_daily_into_quarters(self):
        """Tests the functionality of the filter_daily_into_quarters method

        The method takes in a DataFrame with daily price data and returns a DataFrame
        with quarterly average, high, and low values. This method tests that the 
        resulting DataFrame has the correct values for each quarter, when given
        predetermined data.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: If the function does not return a DataFrame with the
                expected values
        """
        for instance in parser_instance_generator():
            instance.ratios = pd.DataFrame(
                {
                    "start_date": [
                        "2000-01-01",
                        "2000-03-10",
                        "2005-10-11",
                        "2008-02-10",
                    ],
                    "date": ["2000-03-10", "2005-10-11", "2008-02-10", "2010-01-01"],
                },
                index=["idx1", "idx2", "idx3", "idx4"],
            )

            price_dates = instance.create_date_objects_from_strings(
                [
                    "1999-01-01",
                    "2000-01-03",
                    "2000-02-02",
                    "2000-03-10",
                    "2002-01-01",
                    "2005-10-11",
                    "2006-01-01",
                    "2008-02-10",
                    "2010-01-01",
                ]
            )

            price = pd.DataFrame(
                {
                    "High": [i + 10 for i in range(len(price_dates))],
                    "Low": [i + 1 for i in range(len(price_dates))],
                    "Close": [i + 5 for i in range(len(price_dates))],
                    "date": price_dates,
                }
            )
            expected = pd.DataFrame(
                {
                    "stockPriceAverage": [6.5, 8.5, 10.5, 12.0],
                    "stockPriceHigh": [12, 14, 16, 17],
                    "stockPriceLow": [2, 4, 6, 8],
                },
                index=["idx1", "idx2", "idx3", "idx4"],
            )
            instance.price = instance.filter_daily_into_quarters(price)
            self.assertEqual(expected.equals(instance.price), True)

    def test_create_date_objects_from_strings(self):
        """Test if the function can correctly convert a list of date strings to datetime.date objects.

        Args:
            None.

        Returns:
            None.
        """
        date_string_array = ["2000-01-01", "2020-10-12", "2023-01-19", "2019-07-12"]
        expected = [
            dt.date(2000, 1, 1),
            dt.date(2020, 10, 12),
            dt.date(2023, 1, 19),
            dt.date(2019, 7, 12),
        ]
        for instance in parser_instance_generator():
            result = list(instance.create_date_objects_from_strings(date_string_array))
            self.assertEqual(result, expected)

    def test_create_date_objects_from_pd_timestamps(self):
        """Test that a list of `datetime.date` objects is created from a list of pandas
        `Timestamp` objects.

        The method creates a list of `datetime.date` objects by calling
        `create_date_objects_from_pd_timestamps` method of the `Parser` instance with a list of
        pandas `Timestamp` objects as argument. It then compares the result with an expected
        list of `datetime.date` objects.

        Args:
            self: The `ParserTests` instance.

        Returns:
            None.

        Raises:
            AssertionError: If the list of `datetime.date` objects created by the method does
            not match the expected list of `datetime.date` objects.
        """
        from pandas._libs.tslibs.timestamps import Timestamp as ts

        date_string_array = ["2000-01-01", "2020-10-12", "2023-01-19", "2019-07-12"]
        timestamp_array = [ts(i) for i in date_string_array]
        expected = [
            dt.date(2000, 1, 1),
            dt.date(2020, 10, 12),
            dt.date(2023, 1, 19),
            dt.date(2019, 7, 12),
        ]
        for instance in parser_instance_generator():
            result = list(
                instance.create_date_objects_from_pd_timestamps(timestamp_array)
            )
            self.assertEqual(result, expected)

    def test_calculate_PE_ratios(self):
        """Tests the calculation of price-to-earnings (PE) ratios based on income statements and stock prices.
    
        For each parser instance, this function sets the `instance.is_` DataFrame to contain earnings per share (EPS)
        values, the `instance.price` DataFrame to contain stock prices, and the `instance.ratios` DataFrame to an empty
        DataFrame. It then calls the `calculate_PE_ratios` method on the instance and checks whether the resulting
        `instance.ratios` DataFrame matches the expected DataFrame.
        
        The expected DataFrame is generated based on the EPS values and stock prices set for the instance, and it
        contains the calculated PE ratios (PE_avg, PE_low, and PE_high) for each quarter. The test passes if the
        `instance.ratios` DataFrame matches the expected DataFrame.
        """
        for instance in parser_instance_generator():
            instance.is_ = pd.DataFrame({"eps": [5, 10, 15, 20]})

            instance.price = pd.DataFrame(
                {
                    "stockPriceAverage": [20, 40, 120, 400],
                    "stockPriceHigh": [40, 80, 240, 800],
                    "stockPriceLow": [4, 20, 60, 200],
                }
            )

            instance.ratios = pd.DataFrame()
            instance.calculate_PE_ratios()
            expected = pd.DataFrame(
                {
                    "PE_avg": [1.0, 1.0, 2.0, 5.0],
                    "PE_low": [0.2, 0.5, 1.0, 2.5],
                    "PE_high": [2.0, 2.0, 4.0, 10.0],
                }
            )
            self.assertEqual(expected.equals(instance.ratios), True)

    def test_combine_dataframes(self):
        """
        Test case for the `combine_dataframes` method of the `Parser` class.

        The method should combine the `ratios`, `metrics`, `is_`, `price`, and `snp_500` dataframes of a `Parser`
        instance into a single dataframe, using the `date` and `period` columns as indices. The resulting dataframe
        should contain all columns from the original dataframes, and its rows should be sorted by date and period.

        This test case generates a `Parser` instance with pre-defined `ratios`, `metrics`, `is_`, `price`, and `snp_500`
        dataframes, and verifies that the `combine_dataframes` method returns the expected dataframe.

        Returns:
            None.
        """
        df_index = ["a", "b", "c", "d"]
        for instance in parser_instance_generator():
            instance.ratios = pd.DataFrame(
                {"date": [1, 2, 3, 4], "period": [1, 2, 3, 4], "r1": [1, 2, 3, 4]},
                index=df_index,
            )
            instance.metrics = pd.DataFrame(
                {
                    "m1": [4, 5, 6, 7],
                    "m2": [4, 5, 6, 7],
                    "date": [0, 0, 0, 0],
                    "period": [0, 0, 0, 0],
                },
                index=df_index,
            )
            instance.is_ = pd.DataFrame(
                {
                    "date": [0, 0, 0, 0],
                    "period": [0, 0, 0, 0],
                    "is1": [3, 3, 3, 3],
                    "is2": [4, 4, 4, 4],
                },
                index=df_index,
            )
            instance.price = pd.DataFrame(
                {
                    "High": [10, 10, 10, 10],
                    "Low": [1, 2, 2, 1],
                    "Average": [5, 5, 5, 5],
                },
                index=df_index,
            )
            instance.snp_500 = pd.DataFrame(
                {
                    "SHigh": [100, 100, 100, 10],
                    "SLow": [10, 20, 20, 1],
                    "SAverage": [50, 50, 50, 5],
                },
                index=df_index,
            )
            instance.returns = pd.DataFrame(
                {
                    "R1": [100, 100, 100, 10],
                    "R2": [10, 20, 20, 1],
                    "R2": [50, 50, 50, 5],
                },
                index=df_index,
            )
            expected = pd.DataFrame(
                {
                    "date": [1, 2, 3, 4],
                    "period": [1, 2, 3, 4],
                    "r1": [1, 2, 3, 4],
                    "m1": [4, 5, 6, 7],
                    "m2": [4, 5, 6, 7],
                    "is1": [3, 3, 3, 3],
                    "is2": [4, 4, 4, 4],
                    "High": [10, 10, 10, 10],
                    "Low": [1, 2, 2, 1],
                    "Average": [5, 5, 5, 5],
                    "SHigh": [100, 100, 100, 10],
                    "SLow": [10, 20, 20, 1],
                    "SAverage": [50, 50, 50, 5],
                    "R1": [100, 100, 100, 10],
                    "R2": [10, 20, 20, 1],
                    "R2": [50, 50, 50, 5],
                },
                index=df_index,
            )
            result = instance.combine_dataframes()
            self.assertEqual(result.equals(expected), True)

    def test_calculate_returns_from_series(self):
        """Test the `calculate_returns_from_series` method.

        For each instance in the parser_instance_generator, the method sets a
        `price` list and compares the calculated returns using the
        `calculate_returns_from_series` method with the expected returns. The
        expected returns are calculated using the following formula:
        ((price[i] - price[i-1]) / price[i-1]) for i in range(1, len(price))

        Raises:
            AssertionError: If any of the expected returns and calculated returns
            do not match.
        """
        for instance in parser_instance_generator():
            price = [5,4,3,2,1]
            expected = [np.nan, 1.250000, 1.3333333333333333, 1.5, 2.]
            result = instance.calculate_returns_from_series(price)
            self.assertEqual(expected, result)



    def test_calculate_internal_returns(self):
        """
        Tests the calculate_internal_returns method of the Parser class.

        For each Parser instance generated by parser_instance_generator(), sets the
        'price' and 'snp_500' dataframes to predetermined values and calculates the
        internal returns for both dataframes using the calculate_internal_returns
        method. Then, compares the calculated returns to expected values.

        Raises:
            AssertionError: if the calculated returns are not equal to the expected values.
        """
        for instance in parser_instance_generator():
            instance.price = pd.DataFrame([5,4,3,2,1], columns = ['stockPriceAverage'])
            instance.snp_500 = pd.DataFrame([2,4,6,8,10], columns=['S&P500PriceAverage'])
            instance.calculate_internal_returns()
            expected_price =  pd.DataFrame({
                'stockPriceAverage': [5,4,3,2,1],
                'stockPriceRatio_1Q': [np.nan, 1.250000, 1.33333, 1.5, 2.],
                'stockPriceRatio_2Q': [np.nan, np.nan, 1.66667, 2., 3.],
                'stockPriceRatio_3Q': [np.nan, np.nan, np.nan, 2.5, 4.],
                'stockPriceRatio_4Q': [np.nan, np.nan, np.nan, np.nan, 5.]
            })
            pd.testing.assert_frame_equal(expected_price, instance.price)
            
            expected_snp = pd.DataFrame({
                'S&P500PriceAverage': [2,4,6,8,10],
                'snpPriceRatio_1Q': [np.nan, 0.5, 0.66667, 0.75, 0.8],
                'snpPriceRatio_2Q': [np.nan, np.nan, 0.33333, 0.5, 0.6],
                'snpPriceRatio_3Q': [np.nan, np.nan, np.nan, 0.25, 0.4],
                'snpPriceRatio_4Q': [np.nan, np.nan, np.nan, np.nan, 0.2]
            })
            pd.testing.assert_frame_equal(expected_snp, instance.snp_500)


    def test_calculate_relative_returns(self):
        """
        Test the calculation of relative returns based on the price ratios of a security and the S&P 500 index.

        For each parser instance in the generator, set the `ratios`, `price`, and `snp_500` dataframes to pre-defined values.
        Then, calculate the relative returns by dividing the price ratios of the security by those of the S&P 500 index,
        and store them in a new dataframe.

        The expected dataframe is created based on the expected relative returns values.
        The test passes if the calculated and expected dataframes are equal.

        Returns:
            None.
        """
        for instance in parser_instance_generator():
            instance.ratios = pd.DataFrame(index=pd.RangeIndex(0,5))
            instance.price = pd.DataFrame({
                'stockPriceAverage': [5,4,3,2,1],
                'stockPriceRatio_1Q': [np.nan, 1.250000, 1.33333, 1.5, 2.],
                'stockPriceRatio_2Q': [np.nan, np.nan, 1.66667, 2., 3.],
                'stockPriceRatio_3Q': [np.nan, np.nan, np.nan, 2.5, 4.],
                'stockPriceRatio_4Q': [np.nan, np.nan, np.nan, np.nan, 5.]
            })
            instance.snp_500 = pd.DataFrame({
                'S&P500PriceAverage': [2,4,6,8,10],
                'snpPriceRatio_1Q': [np.nan, 0.5, 0.66667, 0.75, 0.8],
                'snpPriceRatio_2Q': [np.nan, np.nan, 0.33333, 0.5, 0.6],
                'snpPriceRatio_3Q': [np.nan, np.nan, np.nan, 0.25, 0.4],
                'snpPriceRatio_4Q': [np.nan, np.nan, np.nan, np.nan, 0.2]
            })
            expected = pd.DataFrame({

                'priceRatioRelativeToS&P_1Q': [np.nan, 2.5, 2., 2., 2.5],
                'priceRatioRelativeToS&P_2Q': [np.nan, np.nan, 5.000060000600006, 4., 5.],
                'priceRatioRelativeToS&P_3Q': [np.nan, np.nan, np.nan, 10., 10.],
                'priceRatioRelativeToS&P_4Q': [np.nan, np.nan, np.nan, np.nan, 25.]
            })

            result = instance.calculate_relative_returns()
            pd.testing.assert_frame_equal(result, expected)


