import streamlit as st
from streamlit_lottie import st_lottie
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import os

from helper import show_table
import plots

__version__ = "0.0.1"
__author__ = "Lukas Calmbach"
__author_email__ = "lcalmbach@gmail.com"
VERSION_DATE = "2023-18-01"
my_name = "climate-ch"
my_kuerzel = "climate-ch"
SOURCE_URL = "https://data.bs.ch/explore/dataset/100227"
GIT_REPO = "https://github.com/lcalmbach/climate-bs"
EMOJI = "🌡️"

START_INDUSTRIAL_PERIOD = 1900

@st.experimental_memo()
def get_lottie():
    ok = True
    r = ""
    try:
        r = requests.get(LOTTIE_URL).json()
    except:
        ok = False
    return r, ok


URL_STATIONS = "https://data.geo.admin.ch/ch.meteoschweiz.klima/nbcn-tageswerte/liste-download-nbcn-d.csv"
BASE_FILE = "./data_previous.pkl"


@st.experimental_memo
def get_data(df_stations: pd.DataFrame):
    if os.path.exists(BASE_FILE):
        previous_data = pd.read_pickle(BASE_FILE)
    else:
        previous_data = get_temperature_data(df_stations, "url_verified_data")
        save_base(previous_data)
    current_data = get_temperature_data(df_stations, "url_current_data")
    result = pd.concat([previous_data, current_data], axis=0, ignore_index=True)
    result = add_time_columns(result)
    result = add_heat_cold_days_columns(result)
    return result


@st.experimental_memo
def get_station_data():
    df_stations = pd.read_csv(URL_STATIONS, sep=";", encoding="cp1252")
    return df_stations


def rename_columns(df):
    def f(x):
        try:
            return np.float32(x)
        except:
            return np.nan

    df.columns = [
        "station",
        "date",
        "radiation",
        "snowpack",
        "nto000d0",
        "prestad0",
        "precip",
        "sunshine_dur",
        "temp_avg",
        "temp_min",
        "temp_max",
        "ure200d0",
    ]
    fields = [
        "station",
        "date",
        "temp_avg",
        "temp_min",
        "temp_max",
    ]
    num_columns = [
        "temp_avg",
        "temp_min",
        "temp_max",
    ]
    for col in num_columns:
        df[col] = df[col].apply(f)
    return df[fields]


def add_heat_cold_days_columns(df):
    # https://www.meteoschweiz.admin.ch/wetter/wetter-und-klima-von-a-bis-z/kuehltag.html
    # https://www.meteoschweiz.admin.ch/wetter/wetter-und-klima-von-a-bis-z.html
    threshold_high = 18.3  # Cooling degree days
    threshold_low = 12  # Heating degree days
    df["cooling_deg_days"] = df.apply(
        lambda x: x["temp_avg"] - threshold_high
        if x["temp_avg"] > threshold_high
        else 0,
        axis=1,
    )
    df["heating_deg_days"] = df.apply(
        lambda x: threshold_high - x["temp_avg"]
        if x["temp_avg"] < threshold_low
        else 0,
        axis=1,
    )
    df.loc[
        df["temp_avg"] < threshold_low, "heating_deg_days"
    ] = 1  # threshold_low - df['temp_avg']
    df["cooling_days"] = df.apply(
        lambda x: 1 if x["temp_avg"] > threshold_high else 0, axis=1
    )
    df["heating_days"] = df.apply(
        lambda x: 1 if x["temp_avg"] < threshold_low else 0, axis=1
    )
    return df


def add_time_columns(df):
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["day_of_year"] = df["date"].dt.dayofyear
    df["day"] = 15
    df["month_date"] = pd.to_datetime(df[["year", "month", "day"]])
    df["jul"] = 7
    df["year_date"] = pd.to_datetime(dict(year=df.year, month=df.jul, day=df.day))
    df = df.drop(["day", "jul"], axis=1)

    return df


def save_base(df):
    df.to_pickle("./data_previous.pkl")


def get_temperature_data(station_df: pd.DataFrame, url_version):
    """Format:
    station/location     Stationskürzel <nat_abbr>
        date                 Datum, Format yyyymmdd

        Parameter            Einheit          Beschreibung
        gre000d0             W/m²             Globalstrahlung; Tagesmittel
        hto000d0             cm               Gesamtschneehöhe; Morgenmessung von 6 UTC
        nto000d0             %                Gesamtbewölkung; Tagesmittel
        prestad0             hPa              Luftdruck auf Stationshöhe (QFE); Tagesmittel
        rre150d0             mm               Niederschlag; Tagessumme 6 UTC - 6 UTC Folgetag
        sre000d0             min              Sonnenscheindauer; Tagessumme
        tre200d0             °C               Lufttemperatur 2 m über Boden; Tagesmittel
        tre200dn             °C               Lufttemperatur 2 m über Boden; Tagesminimum
        tre200dx             °C               Lufttemperatur 2 m über Boden; Tagesmaximum
        ure200d0             %                Relative Luftfeuchtigkeit 2 m über Boden; Tagesmittel


    Args:
        df (pd.DataFrame): _description_

    Returns:
        _type_: _description_
    """
    lst = []
    for index, row in station_df.iterrows():
        _df = pd.read_csv(row[url_version], sep=";", encoding="cp1252")
        lst.append(_df)
    result = pd.concat(lst)
    result = rename_columns(result)
    if url_version == "url_verified_data":
        save_base(result)
    return result


def get_table(df):
    date_min_val = df["temp_min"].min()
    date_max_val = df["temp_max"].max()
    date_min = df.loc[df["temp_min"] == date_min_val, "date"]
    date_min = date_min.iloc[0].strftime("%Y-%m-%d")
    date_max = df.loc[df["temp_max"] == date_max_val, "date"]
    date_max = date_max.iloc[0].strftime("%Y-%m-%d")
    month_stat = (
        df[["year", "month", "temp_avg"]].groupby(["year", "month"]).agg("mean")
    ).reset_index()
    min_month_val = month_stat["temp_avg"].min()
    max_month_val = month_stat["temp_avg"].max()
    month_min = month_stat.loc[month_stat["temp_avg"] == min_month_val]
    month_max = month_stat.loc[month_stat["temp_avg"] == max_month_val]
    month_min = f"{int(month_min.iloc[0]['year'])}-{int(month_min.iloc[0]['month'])}"
    month_max = f"{int(month_max.iloc[0]['year'])}-{int(month_max.iloc[0]['month'])}"
    result = {
        "Parameter": [
            "Minimum temperature [°C]",
            "Maximum temperature [°C]",
            "Date for minimum temperature",
            "Date for maximum temperature",
            "Coldest month average temperature  [°C]",
            "Hottest month average temperature  [°C]",
            "Coldest month",
            "Hottest month",
        ],
        "Value": [
            date_min_val,
            date_max_val,
            date_min,
            date_max,
            min_month_val,
            max_month_val,
            month_min,
            month_max,
        ],
    }
    return pd.DataFrame(result)


def show_summary(row, station_data: pd.DataFrame):
    st.markdown(row.iloc[0]["station"])
    tab = get_table(station_data)
    settings = {"selection_mode": "none", "fit_columns_on_grid_load": True}
    show_table(tab, cols=[], settings=settings)


def add_diff_column(data, climate_normal):
    data = data.join(climate_normal.set_index('month'), on='month', how='inner',  lsuffix='', rsuffix='_agg')
    data['value_diff'] = (data['value'] - data['mean']).astype(float)
    return data


def get_climate_normal(data: pd.DataFrame):
    df = data[data['year'] < START_INDUSTRIAL_PERIOD]
    fields = ['month', 'value']
    group_fields = ['month']
    df = df[fields].groupby(group_fields)['value'].agg(['mean']).reset_index()
    df = df.rename(columns={"value": "mean"})
    return df



def show_time_series(row, df):
    st.markdown(row.iloc[0]["station"])



def show_spiral(row, df):
    def aggregate_data(df, datasource_id: int):
        df = (
            df[["year", "month", "temp_avg"]]
            .groupby(["year", "month"])
            .agg("mean")
            .reset_index()
        )
        df = df.rename(columns={"temp_avg": "value"})
        if datasource_id == 1:
            cn = get_climate_normal(df)
            df = add_diff_column(df, cn)
            df = df.drop(['value'], axis=1)
            df = df.rename(columns={'value_diff': 'value'})

        df = df[df["year"] < datetime.now().year]
        df = df.sort_values(["year", "month"])
        df["z_axis"] = df["year"] + df["month"] / 12
        return df

    
    plot_options = [
        "Monthly average temperature",
        "Difference from climate normal (< 1900)",
    ]
    mode = st.radio(label="Show", options=plot_options)

    temperature_df = aggregate_data(df, plot_options.index(mode))
    min = np.floor(temperature_df["value"].min())
    max = min + np.ceil(temperature_df["value"].max()) + 0.5
    plots.line_chart_3d(temperature_df, min, max)
    with st.expander("Show Data", expanded=False):
        st.table(temperature_df[["year", "month", "value"]])


def main():
    st.markdown('**[Swiss National Basic Climatological Network (Swiss NBCN) stations](https://www.meteoswiss.admin.ch/weather/measurement-systems/land-based-stations/swiss-national-basic-climatological-network.html)**')
    df_stations = get_station_data()

    df_stations.columns = [
        "station",
        "id",
        "WIGOS-ID",
        "data since",
        "station_elev_masl",
        "x",
        "y",
        "latitude",
        "longitude",
        "climate_region",
        "canton",
        "url_verified_data",
        "url_current_data",
    ]
    df_stations = df_stations[df_stations["station"].notna()]
    data = get_data(df_stations)
    col_sel = [
        "id",
        "station",
        "WIGOS-ID",
        "data since",
        "station_elev_masl",
        "climate_region",
    ]
    settings = {"selection_mode": "single", "fit_columns_on_grid_load": True}
    sel_row = show_table(df_stations[col_sel], cols=[], settings=settings)
    if len(sel_row) > 0:
        id = sel_row.iloc[0]["id"]
        station_data = data.query("station == @id")
        tabs = st.tabs(["Summary", "Time series", "Spiral"])
        with tabs[0]:
            show_summary(sel_row, station_data)
        with tabs[1]:
            pass  # show_spiral(sel_row, station_data)
        with tabs[2]:
            show_spiral(sel_row, station_data)


if __name__ == "__main__":
    main()
