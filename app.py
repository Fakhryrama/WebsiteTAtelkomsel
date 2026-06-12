import streamlit as st
import pandas as pd
import folium
import math
from streamlit_folium import st_folium
import shapely.wkt

st.set_page_config(layout="wide")

st.title("🛰️ Dashboard Analisis Masalah Jaringan per Site")
st.markdown("---")

@st.cache_data
def load_data():
    df = pd.read_csv("Tambah_Band.csv") 
    df = df.dropna(subset=['Latitude_Target', 'Longitude_Target', 'Geometry_Pancaran_Sektor_WKT'])
    return df

df = load_data()

col_kiri, col_tengah, col_kanan = st.columns([1.5, 6, 4.5])

with col_kiri:
    st.subheader("🔍 Navigasi")
    site_list = df['Site_ID'].unique().tolist()
    selected_site = st.selectbox(
        "Pilih Site ID:", 
        ["-- Pilih Site --"] + site_list
    )

if selected_site != "-- Pilih Site --":
    filtered_df = df[df['Site_ID'] == selected_site]
    
    coordinates_bound = []
    LUAS_PER_GRID_M2 = 50 * 50 

    for idx, row in filtered_df.iterrows():
        coordinates_bound.append([row['Latitude_Target'], row['Longitude_Target']])
        wkt_polygon = row['Geometry_Pancaran_Sektor_WKT']
        if pd.notnull(wkt_polygon) and isinstance(wkt_polygon, str):
            try:
                poly = shapely.wkt.loads(wkt_polygon)
                site_lon_wkt, site_lat_wkt = poly.exterior.coords[0]
                coordinates_bound.append([site_lat_wkt, site_lon_wkt])
                for lon, lat in poly.exterior.coords:
                    coordinates_bound.append([lat, lon])
            except Exception:
                pass

    if coordinates_bound:
        avg_lat = sum(p[0] for p in coordinates_bound) / len(coordinates_bound)
        avg_lon = sum(p[1] for p in coordinates_bound) / len(coordinates_bound)
    else:
        avg_lat, avg_lon = -7.487, 112.431

    # 👇 PERUBAHAN UTAMA DI SINI 👇
    # Menggunakan URL XYZ Tile dari Google Maps (lyrs=y untuk Satelit + Label Jalan)
    m = folium.Map(
        location=[avg_lat, avg_lon], 
        zoom_start=15, 
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Google Satellite Hybrid'
    )
    # 👆 ---------------------- 👆

    with col_kanan:
        st.subheader("📋 Deskripsi Rinci Site")
        
        for idx, row in filtered_df.iterrows():
            with st.expander(f"🔹 Sektor Target Base: {int(row['Sector_Base_Target'])}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Arah Azimuth:** {row['Arah_Azimuth']}°")
                    st.write(f"**Jarak ke Site:** {row['Jarak_ke_Site_meter']} m")
                with c2:
                    st.write(f"**Jumlah Grid Lemah:** {int(row['Jumlah_Grid_Lemah'])}")
                    st.write(f"**Rata-rata RSRP:** {row['Rata_Rata_RSRP']} dBm")
                
                st.write(f"**Rekomendasi Band:** `{row['Band_Rekomendasi']}`")
                st.warning(f"**Tipe Aksi:** {row['Tipe_Action']}")
                st.info(f"**Alasan Analisis:**\n{row['Reason']}")

    with col_tengah:
        st.subheader(f"📍 Tampilan Peta: {selected_site}")
        
        for idx, row in filtered_df.iterrows():
            problem_lat = row['Latitude_Target']
            problem_lon = row['Longitude_Target']
            jml_grid = row['Jumlah_Grid_Lemah']
            wkt_polygon = row['Geometry_Pancaran_Sektor_WKT']
            tipe_action = row['Tipe_Action']
            reason = row['Reason']
            band_rekomendasi = row['Band_Rekomendasi']
            
            try:
                rsrp = float(str(row['Rata_Rata_RSRP']).replace(',', '.'))
            except ValueError:
                rsrp = 0.0

            site_lat, site_lon = None, None

            if pd.notnull(wkt_polygon) and isinstance(wkt_polygon, str):
                try:
                    poly = shapely.wkt.loads(wkt_polygon)
                    locations = [(lat, lon) for lon, lat in poly.exterior.coords]
                    site_lon_wkt, site_lat_wkt = poly.exterior.coords[0]
                    site_lat = site_lat_wkt
                    site_lon = site_lon_wkt
                    
                    folium.Polygon(
                        locations=locations,
                        color="cyan", # Diubah ke cyan agar lebih kontras dengan background satelit yang gelap
                        weight=2,
                        fill=True,
                        fill_opacity=0.25,
                        tooltip=f"Sektor Cakupan: {row['Sector_Base_Target']}"
                    ).add_to(m)
                except Exception:
                    pass 

            if site_lat is not None and site_lon is not None:
                # Mengubah icon marker menjadi putih agar terlihat jelas di atas citra satelit
                folium.Marker(
                    location=[site_lat, site_lon],
                    tooltip=f"Site ID: {selected_site}",
                    icon=folium.Icon(color="black", icon="info-sign")
                ).add_to(m)

                luas_total = jml_grid * LUAS_PER_GRID_M2
                radius_m = math.sqrt(luas_total / math.pi)
                color = 'red' if rsrp < -105 else 'orange'

                folium.Circle(
                    location=[problem_lat, problem_lon],
                    radius=radius_m,
                    color=color,
                    weight=3, # Ditebalkan sedikit agar garis luarnya jelas di atas rumah/pohon
                    fill=True,
                    fill_opacity=0.6,
                    tooltip=f"Problem Area Sektor {row['Sector_Base_Target']}"
                ).add_to(m)
                
                folium.PolyLine(
                    locations=[[site_lat, site_lon], [problem_lat, problem_lon]],
                    color="red",
                    weight=3,
                    dash_array='5, 5'
                ).add_to(m)

        if coordinates_bound:
            m.fit_bounds(coordinates_bound)

        st_folium(m, width=750, height=600, key=f"map_{selected_site}")

else:
    with col_tengah:
        st.info("💡 Silakan pilih Site ID pada menu navigasi sebelah kiri untuk memulai analisis.")