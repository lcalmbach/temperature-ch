# NBCN-Data-Browser
[This application](https://lcalmbach-temperature-ch-app-rzexhr.streamlit.app/) allows to explore daily temperature data from 29 stations of the Swiss National Basel Climatology Network (NBCN). The Data is published by its owner MeteoSuisse on [opendata.swiss](https://opendata.swiss/de/organization/bundesamt-fur-meteorologie-und-klimatologie-meteoschweiz). NBCN-Data-Browser is written in python using the framework [streamlit](https://streamlit.io/) and the libraries [plotly](https://plotly.com/python/) and [altair](https://altair-viz.github.io/). To install the app locally proceed as follows:

```
> git clone https://github.com/lcalmbach/temperature-ch.git
> cd temperature-ch
> python -m venv env
> env\scripts\activate
> pip install -r requirements.txt
> streamlit run app.py
```