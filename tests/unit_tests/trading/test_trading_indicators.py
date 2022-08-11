import pandas as pd
from numpy import float64, ceil
from statsmodels.compat.pandas import assert_series_equal, assert_frame_equal
from models.Trading import TechnicalAnalysis


def test_should_calculate_add_change_pcnt():
    """
      Adds the close percentage to the DataFrame : close_pc
      Adds the cumulative returns the DataFrame : close_cpc

      Excellent video to understand cumulative returns : https://www.youtube.com/watch?v=fWHQwqT3lNY
    """

    # GIVEN a series of values
    closes_list = [0.0003, 0.0004, 0.0010, 0.0020, 0.0009]
    df = pd.DataFrame({'date': ['2021-10-10 14:30:00',
                                '2021-10-10 14:31:00',
                                '2021-10-10 14:32:00',
                                '2021-10-10 14:33:00',
                                '2021-10-10 14:34:00'],
                       'close': closes_list})
    df['date'] = pd.to_datetime(df['date'], format="%Y-%d-%m %H:%M:%S")
    df.set_index(['date'])

    ta = TechnicalAnalysis(df)

    # WHEN calculate the percentage evolution and cumulative returns percentage
    ta.add_change_pcnt()

    # THEN percentage evolution and cumulative returns percentage should be added to dataframe
    actual = ta.get_df()

    close_pc = [
        calculate_percentage_evol(closes_list[0], closes_list[0]),
        calculate_percentage_evol(closes_list[0], closes_list[1]),
        calculate_percentage_evol(closes_list[1], closes_list[2]),
        calculate_percentage_evol(closes_list[2], closes_list[3]),
        calculate_percentage_evol(closes_list[3], closes_list[4]),
    ]

    close_cpc = []
    close_cpc.append(0.000000)
    close_cpc.append((1 + close_pc[1]) * (1 + close_cpc[0]) - 1)
    close_cpc.append((1 + close_pc[2]) * (1 + close_cpc[1]) - 1)
    close_cpc.append((1 + close_pc[3]) * (1 + close_cpc[2]) - 1)
    close_cpc.append((1 + close_pc[4]) * (1 + close_cpc[3]) - 1)

    expected = pd.DataFrame({
        'date': ['2021-10-10 14:30:00',
                 '2021-10-10 14:31:00',
                 '2021-10-10 14:32:00',
                 '2021-10-10 14:33:00',
                 '2021-10-10 14:34:00'],
        'close': closes_list,
        'close_pc': close_pc,
        'close_cpc': close_cpc
    })
    expected['date'] = pd.to_datetime(df['date'], format="%Y-%d-%m %H:%M:%S")
    expected.set_index(['date'])
    assert_frame_equal(actual, expected)


def test_should_calculate_add_cma():
    """
      Adds the Cumulative Moving Average (CMA) to the DataFrame : cma
    """

    # GIVEN a series of values
    closes_list = [0.0003, 0.0004, 0.0010, 0.0020, 0.0009]
    df = pd.DataFrame({'date': ['2021-10-10 14:30:00',
                                '2021-10-10 14:31:00',
                                '2021-10-10 14:32:00',
                                '2021-10-10 14:33:00',
                                '2021-10-10 14:34:00'],
                       'close': closes_list})
    df['date'] = pd.to_datetime(df['date'], format="%Y-%d-%m %H:%M:%S")
    df.set_index(['date'])

    ta = TechnicalAnalysis(df)

    # WHEN calculate the cumulative moving average
    ta.add_cma()

    # THEN Cumulative Moving Average should be added to dataframe
    actual = ta.get_df()
    expected = pd.DataFrame({
        'date': ['2021-10-10 14:30:00',
                 '2021-10-10 14:31:00',
                 '2021-10-10 14:32:00',
                 '2021-10-10 14:33:00',
                 '2021-10-10 14:34:00'],
        'close': closes_list,
        'cma': [
            calculate_mean_on_range(0, 1, closes_list),
            calculate_mean_on_range(0, 2, closes_list),
            calculate_mean_on_range(0, 3, closes_list),
            calculate_mean_on_range(0, 4, closes_list),
            calculate_mean_on_range(0, 5, closes_list),
        ]
    })
    expected['date'] = pd.to_datetime(df['date'], format="%Y-%d-%m %H:%M:%S")
    expected.set_index(['date'])
    assert_frame_equal(actual, expected)


def test_should_calculate_add_sma_20():
    """
      Add the Simple Moving Average (SMA) to the DataFrame :
    """

    # GIVEN a series of values
    closes_list = [0.0003, 0.0004, 0.0010, 0.0020, 0.0009, 0.0008, 0.0009, 0.0010, 0.0012, 0.0015, 0.0025,
                   0.0015, 0.0014, 0.0016, 0.0030, 0.0032, 0.0035, 0.0024, 0.0023, 0.0022, 0.0021, 0.0020]
    df = pd.DataFrame({'date': ['2021-10-10 14:30:00',
                                '2021-10-10 14:31:00',
                                '2021-10-10 14:32:00',
                                '2021-10-10 14:33:00',
                                '2021-10-10 14:34:00',
                                '2021-10-10 14:35:00',
                                '2021-10-10 14:36:00',
                                '2021-10-10 14:37:00',
                                '2021-10-10 14:38:00',
                                '2021-10-10 14:39:00',
                                '2021-10-10 14:40:00',
                                '2021-10-10 14:41:00',
                                '2021-10-10 14:42:00',
                                '2021-10-10 14:43:00',
                                '2021-10-10 14:44:00',
                                '2021-10-10 14:45:00',
                                '2021-10-10 14:46:00',
                                '2021-10-10 14:47:00',
                                '2021-10-10 14:48:00',
                                '2021-10-10 14:49:00',
                                '2021-10-10 14:50:00',
                                '2021-10-10 14:51:00'],
                       'close': closes_list})
    df['date'] = pd.to_datetime(df['date'], format="%Y-%d-%m %H:%M:%S")
    df.set_index(['date'])

    ta = TechnicalAnalysis(df)

    # WHEN calculate the cumulative moving average 20
    ta.add_sma(20)

    # THEN
    actual = ta.get_df()
    expected = pd.DataFrame({
        'date': ['2021-10-10 14:30:00',
                 '2021-10-10 14:31:00',
                 '2021-10-10 14:32:00',
                 '2021-10-10 14:33:00',
                 '2021-10-10 14:34:00',
                 '2021-10-10 14:35:00',
                 '2021-10-10 14:36:00',
                 '2021-10-10 14:37:00',
                 '2021-10-10 14:38:00',
                 '2021-10-10 14:39:00',
                 '2021-10-10 14:40:00',
                 '2021-10-10 14:41:00',
                 '2021-10-10 14:42:00',
                 '2021-10-10 14:43:00',
                 '2021-10-10 14:44:00',
                 '2021-10-10 14:45:00',
                 '2021-10-10 14:46:00',
                 '2021-10-10 14:47:00',
                 '2021-10-10 14:48:00',
                 '2021-10-10 14:49:00',
                 '2021-10-10 14:50:00',
                 '2021-10-10 14:51:00'],
        'close': closes_list,
        'sma20': [calculate_mean_on_range(0, 1, closes_list),
                  calculate_mean_on_range(0, 2, closes_list),
                  calculate_mean_on_range(0, 3, closes_list),
                  calculate_mean_on_range(0, 4, closes_list),
                  calculate_mean_on_range(0, 5, closes_list),
                  calculate_mean_on_range(0, 6, closes_list),
                  calculate_mean_on_range(0, 7, closes_list),
                  calculate_mean_on_range(0, 8, closes_list),
                  calculate_mean_on_range(0, 9, closes_list),
                  calculate_mean_on_range(0, 10, closes_list),
                  calculate_mean_on_range(0, 11, closes_list),
                  calculate_mean_on_range(0, 12, closes_list),
                  calculate_mean_on_range(0, 13, closes_list),
                  calculate_mean_on_range(0, 14, closes_list),
                  calculate_mean_on_range(0, 15, closes_list),
                  calculate_mean_on_range(0, 16, closes_list),
                  calculate_mean_on_range(0, 17, closes_list),
                  calculate_mean_on_range(0, 18, closes_list),
                  calculate_mean_on_range(0, 19, closes_list),
                  calculate_mean_on_range(0, 20, closes_list),
                  calculate_mean_on_range(1, 21, closes_list),
                  calculate_mean_on_range(2, 22, closes_list)
                  ]
    })
    expected['date'] = pd.to_datetime(df['date'], format="%Y-%d-%m %H:%M:%S")
    expected.set_index(['date'])

    assert_frame_equal(actual, expected)


def calculate_mean_on_range(start, end, list) -> float64:
    """
    Calculates de mean on a range of values
    """
    return float(sum(list[start:end]) / (end - start))


def calculate_percentage_evol(start, end) -> float64:
    """
    Calculates the evolution percentage for 2 values
    """
    return end / start - 1
