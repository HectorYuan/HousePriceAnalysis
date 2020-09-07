#%%
import pandas as pd
from geopy.distance import geodesic
#%%
house_data = pd.read_csv(r"上海全市小区信息_neo.csv")
rmsqure = (31.228816, 121.475164)

#%%

house_data['距离市中心'] = house_data.apply(lambda x: geodesic((x['1'],x['0']),rmsqure).km,axis=1)


#%%
house_data.to_csv("上海全市小区信息_neo.csv")