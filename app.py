import streamlit as st
import pandas as pd
import numpy as np
from streamlit_option_menu import option_menu
from datetime import datetime
import os

from helper import show_table
from swiss_nbcn import NbcnBrowser

__version__ = "0.0.5"
__author__ = "Lukas Calmbach"
__author_email__ = "lcalmbach@gmail.com"
VERSION_DATE = "2023-22-01"
my_name = "Swiss.NBCN Data Explorer"
SOURCE_URL = "https://opendata.swiss/de/dataset/klimamessnetz-tageswerte"
GIT_REPO = "https://github.com/lcalmbach/temperature-ch"
EMOJI = "🌡️"


def init():
    st.set_page_config(  # Alternate names: setup_page, page, layout
        initial_sidebar_state="auto",
        page_title=my_name,
        page_icon="🌍",
        layout="wide",
    )
    load_css()
    st.sidebar.markdown(f"## {my_name}")


def load_css():
    with open("./style.css") as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)


def get_info():
    text = f"""<div style="background-color:#34282C; padding: 10px;border-radius: 15px; border:solid 1px white;">
    <small>App by <a href="mailto:{__author_email__}">{__author__}</a><br>
    Version: {__version__} ({VERSION_DATE})<br>
    Data source: <a href="{SOURCE_URL}">MeteoSuisse</a><br>
    <a href="{GIT_REPO}">git-repo</a></small></div>
    """
    return text


def main():
    init()
    menu_options = [
        "Summarize",
        "Time Series",
        "3D Spiral View",
        "Data",
        "About NBCN Browser",
    ]
    with st.sidebar:
        # https://icons.getbootstrap.com/
        menu_action = option_menu(
            None,
            menu_options,
            icons=["table", "graph-up", "badge-3d", "server", "info"],
            menu_icon="cast",
            default_index=0,
        )
    menu_id = menu_options.index(menu_action)
    app = NbcnBrowser()

    sel_row = pd.DataFrame()
    if menu_id < (len(menu_options) - 1):
        sel_row = app.get_station()

    if len(sel_row) > 0:
        if menu_options.index(menu_action) == 0:
            app.show_summary(sel_row)
        elif menu_options.index(menu_action) == 1:
            app.get_user_options("time-series")
            app.show_time_series(sel_row)
        elif menu_options.index(menu_action) == 2:
            app.show_spiral(sel_row)
        elif menu_options.index(menu_action) == 3:
            app.get_user_options("data")
            app.show_data(sel_row)
    elif menu_options.index(menu_action) == 4:
        app.show_info()

    st.sidebar.markdown(get_info(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
