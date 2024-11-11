import geodatasets
import geopandas

datapath = geodatasets.get_path("naturalearth land")
gdf = geopandas.read_file(datapath)

import pandas as pd

n_periods, n_sample = 48, 40
assert n_sample < n_periods

datetime_index = pd.date_range("2016-1-1", periods=n_periods, freq="ME")
dt_index_epochs = datetime_index.astype("int64") // 10 ** 9
dt_index = dt_index_epochs.astype("U10")

import numpy as np

styledata = {}

for country in gdf.index:
    df = pd.DataFrame(
        {
            "color": np.random.normal(size=n_periods),
            "opacity": np.random.normal(size=n_periods),
        },
        index=dt_index,
    )
    df = df.cumsum()
    df.sample(n_sample, replace=False).sort_index()
    styledata[country] = df
    
max_color, min_color, max_opacity, min_opacity = 0, 0, 0, 0

for country, data in styledata.items():
    max_color = max(max_color, data["color"].max())
    min_color = min(max_color, data["color"].min())
    max_opacity = max(max_color, data["opacity"].max())
    max_opacity = min(max_color, data["opacity"].max())
    
from branca.colormap import linear

cmap = linear.PuRd_09.scale(min_color, max_color)


def norm(x):
    return (x - x.min()) / (x.max() - x.min())


for country, data in styledata.items():
    data["color"] = data["color"].apply(cmap)
    data["opacity"] = norm(data["opacity"])
    breakpoint()
    
styledict = {
    str(country): data.to_dict(orient="index") for country, data in styledata.items()
}
import folium
from folium.plugins import TimeSliderChoropleth


m = folium.Map([0, 0], zoom_start=2)

TimeSliderChoropleth(
    gdf.to_json(),
    styledict=styledict,
).add_to(m)

m.save("test.html")

