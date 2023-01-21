import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os

import plots
from helper import show_table


URL_STATIONS = "https://data.geo.admin.ch/ch.meteoschweiz.klima/nbcn-tageswerte/liste-download-nbcn-d.csv"
BASE_FILE = "./data_previous.pkl"
START_INDUSTRIAL_PERIOD = 1900


class NbcnBrowser:
    def __init__(self):
        self.df_stations_full = self.get_stations()
        self.data = self.get_data(self.df_stations_full)
        self._sel_station = ""
        self.station_data = pd.DataFrame()
        self.resolution_options = ["Year", "Month", "Day"]
        self.parameter = "temp_avg"
        self.parameter_options = [
            "temp_avg",
            "heating_deg_days",
            "cooling_days",
            "heating_days",
        ]
        self.parameter_titles = {
            "temp_avg": "Avg Temperature [°C]",
            "heating_deg_days": "Heating degree days",
            "cooling_days": "Cooling days",
            "heating_days": "Heating days",
        }

    @property
    def sel_station(self):
        return self._sel_station

    @sel_station.setter
    def sel_station(self, id):
        self._sel_station = id
        self.data = self.data[self.data["station"] == id]
        self.year_min, self.year_max = self.data["year"].min(), self.data["year"].max()

    @property
    def station_list_disp(self):
        disp_fields = [
            "id",
            "station",
            "data since",
            "station_elev_masl",
            "climate_region",
            "canton",
        ]
        return self.df_stations_full[disp_fields]

    @st.experimental_memo
    def get_data(_self, df_stations: pd.DataFrame):
        if os.path.exists(BASE_FILE):
            previous_data = pd.read_pickle(BASE_FILE)
        else:
            previous_data = _self.get_temperature_data(df_stations, "url_verified_data")
            _self.save_base(previous_data)
        current_data = _self.get_temperature_data(df_stations, "url_current_data")
        result = pd.concat([previous_data, current_data], axis=0, ignore_index=True)
        result = _self.add_time_columns(result)
        result = _self.add_heat_cold_days_columns(result)
        return result

    @st.experimental_memo
    def get_stations(_self):
        _df = pd.read_csv(URL_STATIONS, sep=";", encoding="cp1252")
        _df.columns = [
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
        _df = _df[_df["station"].notna()]
        return _df

    def rename_columns(self, df):
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

    def add_heat_cold_days_columns(self, df):
        # https://www.meteoschweiz.admin.ch/wetter/wetter-und-klima-von-a-bis-z/kuehltag.html
        # https://www.meteoschweiz.admin.ch/wetter/wetter-und-klima-von-a-bis-z.html

        outside_temp = 12  # Heating degree days
        room_temp = 20
        threshold_high = 18.3  # Cooling degree days
        # todo: find out official definition
        # df["cooling_deg_days"] = df.apply(
        #    lambda x: x["temp_avg"] - threshold_high
        #    if x["temp_avg"] > threshold_high
        #    else 0,
        #    axis=1,
        # )
        df["heating_deg_days"] = df.apply(
            lambda x: room_temp - x["temp_avg"] if x["temp_avg"] < outside_temp else 0,
            axis=1,
        )
        df["heating_days"] = df.apply(
            lambda x: 1 if x["temp_avg"] < outside_temp else 0, axis=1
        )
        df["cooling_days"] = df.apply(
            lambda x: 1 if x["temp_avg"] > threshold_high else 0, axis=1
        )
        return df

    def add_time_columns(self, df):
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

    def save_base(self, df):
        df.to_pickle("./data_previous.pkl")

    def get_temperature_data(self, station_df: pd.DataFrame, url_version):
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
        result = self.rename_columns(result)
        if url_version == "url_verified_data":
            self.save_base(result)
        return result

    def get_summary_table(self, df):
        date_min_val = df["temp_min"].min()
        date_max_val = df["temp_max"].max()
        date_min = df.loc[df["temp_min"] == date_min_val, "date"]
        date_min = date_min.iloc[0].strftime("%Y-%m-%d")
        date_max = df.loc[df["temp_max"] == date_max_val, "date"]
        date_max = date_max.iloc[0].strftime("%Y-%m-%d")

        month_fields = ["year", "month", "temp_avg", "heating_deg_days"]
        month_stat = (
            df[month_fields]
            .groupby(["year", "month"])
            .agg({"temp_avg": "mean", "heating_deg_days": "sum"})
        ).reset_index()
        min_month_val = month_stat["temp_avg"].min()
        max_month_val = month_stat["temp_avg"].max()
        month_min = month_stat.loc[month_stat["temp_avg"] == min_month_val]
        month_max = month_stat.loc[month_stat["temp_avg"] == max_month_val]
        month_min = (
            f"{int(month_min.iloc[0]['year'])}-{int(month_min.iloc[0]['month'])}"
        )
        month_max = (
            f"{int(month_max.iloc[0]['year'])}-{int(month_max.iloc[0]['month'])}"
        )

        year_fields = ["year", "temp_avg", "heating_deg_days"]
        year_stat = (
            df.loc[df["year"] < datetime.now().year, year_fields]
            .groupby(["year"])
            .agg({"temp_avg": "mean", "heating_deg_days": "sum"})
            .reset_index()
        )
        year_stat.columns = year_fields

        min_year_val = year_stat["temp_avg"].min()
        max_year_val = year_stat["temp_avg"].max()
        year_min = (year_stat.loc[year_stat["temp_avg"] == min_year_val, "year"]).iloc[
            0
        ]
        year_max = (year_stat.loc[year_stat["temp_avg"] == max_year_val, "year"]).iloc[
            0
        ]
        result = {
            "Parameter": [
                "Minimum temperature [°C]",
                "Maximum temperature [°C]",
                "Coldest monthly average temperature [°C]",
                "Hottest monthly average temperature[°C]",
                "Coldest yearly average temperature [°C]",
                "Hottest yearly average temperature [°C]",
            ],
            "Date": [
                date_min,
                date_max,
                month_min,
                month_max,
                year_min,
                year_max,
            ],
            "Value": [
                f"{date_min_val :.1f}",
                f"{date_max_val :.1f}",
                f"{min_month_val :.1f}",
                f"{max_month_val :.1f}",
                f"{min_year_val :.1f}",
                f"{max_year_val :.1f}",
            ],
        }
        return pd.DataFrame(result), month_stat, year_stat

    def station_link(self, row):
        return f"🔗[{row.iloc[0]['station']}](https://www.meteoswiss.admin.ch/services-and-publications/applications/measurement-values-and-measuring-networks.html#param=messnetz-klima&lang=en&station={row.iloc[0]['id']}&chart=year&compare=y)"

    def show_summary(self, row):
        st.markdown(self.station_link(row))
        summary, month_stat, year_stat = self.get_summary_table(self.data)
        st.markdown(f"Summary {year_stat['year'].min()} - {year_stat['year'].max()}")
        st.write(summary)
        st.markdown("Yearly temperature average and heating degree days")
        st.write(year_stat)
        st.markdown("Monthly temperature average and heating degree days")
        st.write(month_stat)

    def add_diff_column(self, data, climate_normal):
        data = data.join(
            climate_normal.set_index("month"),
            on="month",
            how="inner",
            lsuffix="",
            rsuffix="_agg",
        )
        data["value_diff"] = (data["value"] - data["mean"]).astype(float)
        return data

    def get_climate_normal(self, data: pd.DataFrame):
        df = data[data["year"] < START_INDUSTRIAL_PERIOD]
        fields = ["month", "value"]
        group_fields = ["month"]
        df = df[fields].groupby(group_fields)["value"].agg(["mean"]).reset_index()
        df = df.rename(columns={"value": "mean"})
        return df

    def get_user_options(self, type: str):
        with st.sidebar.expander("⚙️ Settings", expanded=True):
            st.write(type)
            if type == "time-series":
                self.parameter = st.selectbox(
                    "Parameter", options=self.parameter_options
                )
            self.resolution = st.selectbox(
                "Time Resolution", self.resolution_options, key="data_resolution"
            )
            self.years = st.select_slider(
                label="Years",
                options=list(range(self.year_min, self.year_max + 1)),
                value=[self.year_min, self.year_max],
                key="data_years",
            )
            if type == "time-series":
                self.show_regression = st.checkbox("Show Regression")
                self.show_average = st.checkbox("Show Average")

    def filter_data(self):
        if self.resolution_options.index(self.resolution) == 2:
            df = self.data
            self.x_var = "date"
        elif self.resolution_options.index(self.resolution) == 1:
            all_fields = [
                "year",
                "month",
                "month_date",
                "temp_avg",
                "heating_deg_days",
                "cooling_days",
                "heating_days",
            ]
            df = (
                self.data[all_fields]
                .groupby(["year", "month", "month_date"])
                .agg(
                    {
                        "temp_avg": ["mean"],
                        "heating_deg_days": ["sum"],
                        "cooling_days": ["sum"],
                        "heating_days": ["sum"],
                    }
                )
                .reset_index()
            )
            # after aggregation, column names are composed field-agg
            df.columns = all_fields
            self.x_var = "month_date"
        elif self.resolution_options.index(self.resolution) == 0:
            all_fields = [
                "year",
                "year_date",
                "temp_avg",
                "heating_deg_days",
                "cooling_days",
                "heating_days",
            ]
            df = (
                self.data[all_fields]
                .groupby(["year", "year_date"])
                .agg(
                    {
                        "temp_avg": ["mean"],
                        "heating_deg_days": ["sum"],
                        "cooling_days": ["sum"],
                        "heating_days": ["sum"],
                    }
                )
                .reset_index()
            )
            df.columns = all_fields
            df = df[df["year"] < datetime.now().year]
            self.x_var = "year_date"
        if self.years != [self.year_min, self.year_max]:
            df = df[(df["year"] >= self.years[0]) & (df["year"] <= self.years[1])]
        return df

    def show_data(self, row):
        st.markdown(self.station_link(row))
        self.resolution = self.resolution_options[2]
        data_df = self.filter_data()
        st.write(data_df)
        csv = data_df.to_csv(index=False).encode("utf-8")
        text = "The table above includes additional columns as compared to the original MeteoSuisse data. The original data can be downloaded [here](https://opendata.swiss/de/dataset/klimamessnetz-tageswerte)."
        st.markdown(text, unsafe_allow_html=True)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name=f'{row.iloc[0]["station"]}.csv',
            mime="text/csv",
        )

    def show_time_series(self, row):
        st.markdown(self.station_link(row))
        plot_df = self.filter_data()
        settings = {
            "x": self.x_var,
            "y": self.parameter,
            "color": "station",
            "x_title": "",
            "y_title": self.parameter_titles[self.parameter],
            "tooltip": [self.x_var, self.parameter],
            "width": 1000,
            "height": 400,
            "title": "",
            "show_regression": self.show_regression,
            "show_average": self.show_average,
        }
        settings["y_domain"] = [
            plot_df[self.parameter].min() - 1,
            plot_df[self.parameter].max() + 1,
        ]
        plots.time_series_chart(plot_df, settings)

    def show_spiral(self, row):
        def aggregate_data(df, datasource_id: int):
            df = (
                df[["year", "month", self.parameter]]
                .groupby(["year", "month"])
                .agg("mean")
                .reset_index()
            )
            df = df.rename(columns={"temp_avg": "value"})
            if datasource_id == 1:
                cn = self.get_climate_normal(df)
                df = self.add_diff_column(df, cn)
                df = df.drop(["value"], axis=1)
                df = df.rename(columns={"value_diff": "value"})

            df = df[df["year"] < datetime.now().year]
            df = df.sort_values(["year", "month"])
            return df

        st.markdown(self.station_link(row))
        station = row.iloc[0]["station"]
        plot_options = [
            "Monthly average temperature",
            "Difference from climate normal (< 1900)",
        ]
        mode = st.radio(label="Show", options=plot_options)
        mode_id = plot_options.index(mode)
        temperature_df = aggregate_data(self.data, mode_id)
        min = np.floor(temperature_df["value"].min()) - 0.5
        max = min + np.ceil(temperature_df["value"].max()) + 0.5
        title = [
            f"Spiral View of average monthly temperature at {station}",
            f"Spiral View of monthly temperature difference from preindustrial (<1900) climate normal at {station}",
        ]
        settings = {"min": min, "max": max, "value": "value", "title": title[mode_id]}

        plots.line_chart_3d(temperature_df, settings)
        with st.expander("Show Data", expanded=False):
            st.table(temperature_df[["year", "month", "value"]])

    def get_station(self):
        text = "Select a station"
        with st.expander(text, expanded=True):
            st.markdown(
                f"🔗[Swiss National Basic Climatological Network (Swiss NBCN) stations](https://www.meteoswiss.admin.ch/weather/measurement-systems/land-based-stations/swiss-national-basic-climatological-network.html) ({len(self.station_list_disp)})"
            )
            settings = {
                "selection_mode": "single",
                "fit_columns_on_grid_load": False,
                "height": 300,
            }
            sel_row = show_table(self.station_list_disp, cols=[], settings=settings)
        if len(sel_row) > 0:
            self.sel_station = sel_row.iloc[0]["id"]
            return sel_row

    def show_info(self):
        with open("./info.md") as f:
            text = f.read()
        st.markdown(text)
