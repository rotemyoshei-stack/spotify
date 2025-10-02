import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import arabic_reshaper
from bidi.algorithm import get_display
import os, json

# --- פונקציה לסידור טקסט בעברית ---
def fix_hebrew(text):
    if isinstance(text, str):
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    return text

# קיצור לשימוש נוח
h = fix_hebrew

# --- בחירת תיקייה ---
st.sidebar.header(h("📂 בחירת תיקייה"))
folder_name = st.sidebar.text_input(h("שם תיקייה עם קבצי JSON"), "data_folder")

# נבדוק אם התיקייה קיימת
if os.path.exists(folder_name) and os.path.isdir(folder_name):
    json_files = [f for f in os.listdir(folder_name) if f.endswith(".json")]
    
    if json_files:
        all_data = []
        for file_name in json_files:
            file_path = os.path.join(folder_name, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data if isinstance(data, list) else [data])
        
        df = pd.DataFrame(all_data)
        st.sidebar.success(h(f"✅ נטענו {len(json_files)} קבצים"))
    else:
        st.sidebar.warning(h("⚠️ אין קבצי JSON בתיקייה"))
        df = None
else:
    st.sidebar.warning(h("⚠️ התיקייה לא קיימת"))
    df = None

if df is not None and not df.empty:
    # --- עיבוד ראשוני ---
    # שומרים עותק מקורי לשימוש פנימי, ונכין עותק להצגה
    # (לא משנים שמות העמודות המקוריות כי הקוד משתמש בהן)
    df['endTime'] = pd.to_datetime(df['endTime'])
    df['secondsPlayed'] = df['msPlayed'] / 1000
    df['timePlayed'] = pd.to_timedelta(df['secondsPlayed'], unit='second')
    df['startTime'] = df['endTime'] - df['timePlayed']
    df['weekNum'] = df['startTime'].dt.isocalendar().week

    st.header(h("🎧 ברוכים הבאים — Spotify Wrapped משודרג"))

    # --- ניתוח אחוזי האזנה ---
    aggregated_data = df.groupby(['trackName','artistName']).agg(
        avg_play_time=('timePlayed', 'mean'),
        times_played=('trackName', 'count'),
        max_song_length=('timePlayed', 'max')
    ).reset_index()

    aggregated_data['avg_percentage'] = (aggregated_data['avg_play_time'] / aggregated_data['max_song_length'])*100
    aggregated_data = aggregated_data[aggregated_data['times_played'] > 1]
    aggregated_data = aggregated_data[aggregated_data['max_song_length'] > pd.Timedelta(seconds=60)]
    aggregated_data = aggregated_data.sort_values(by='avg_percentage', ascending=False)

    st.header(h("📊 אחוזי האזנה לשירים"))

    if not aggregated_data.empty:
        # הצגה ידידותית בעברית של הטבלה
        aggregated_display = aggregated_data.copy()
        aggregated_display['trackName'] = aggregated_display['trackName'].apply(lambda x: h(x) if isinstance(x, str) else x)
        aggregated_display['artistName'] = aggregated_display['artistName'].apply(lambda x: h(x) if isinstance(x, str) else x)
        aggregated_display.rename(columns={
            'trackName': h('שם שיר'),
            'artistName': h('שם אמן'),
            'avg_play_time': h('משך ממוצע'),
            'times_played': h('כמות האזנות'),
            'max_song_length': h('אורך שיר מקסימלי'),
            'avg_percentage': h('אחוז האזנה')
        }, inplace=True)

        st.dataframe(aggregated_display.head(15))

        # בחירת השיר הטוב והגרוע (בהתאם לסינון הנ"ל)
        best_song = aggregated_data.sort_values(by=['times_played','avg_percentage'], ascending=[False, False]).iloc[0]
        worst_song = aggregated_data.sort_values(by='avg_percentage', ascending=True).iloc[0]

        st.success(h("🎶 השיר עם אחוז ההאזנה הגבוה ביותר הוא ") + " " + h(best_song['trackName']) + f" ({best_song['avg_percentage']:.1f}%)")
        st.warning(h("⚠️ השיר עם אחוז ההאזנה הנמוך ביותר הוא ") + " " + h(worst_song['trackName']) + f" ({worst_song['avg_percentage']:.1f}%)")

        # גרף ברים לשירים עם אחוזים נמוכים
        st.subheader(h("📉 שירים עם אחוזי האזנה נמוכים ביותר"))
        low_songs = aggregated_data.sort_values(by='avg_percentage').head(5)
        if not low_songs.empty:
            fig, ax = plt.subplots(figsize=(8,4))
            x = low_songs['trackName'].apply(lambda s: h(s) if isinstance(s, str) else s)
            y = low_songs['avg_percentage']
            ax.bar(x, y)
            ax.set_xlabel(h('שם שיר'))
            ax.set_ylabel(h('אחוז האזנה'))
            ax.set_title(h('שירים עם אחוזי האזנה נמוכים ביותר'))
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig)
    else:
        st.info(h("אין נתונים מספקים לניתוח אחוזי האזנה לאחר הסינון"))

    # --- שירים לפי שבועות ---
    st.header(h("📅 כמה שבועות שיר נשמע"))
    df_unique_weeks = df[['trackName','weekNum']].drop_duplicates().sort_values(by=['weekNum','trackName'])
    weeks_aggregated_data = df_unique_weeks.groupby('trackName').agg(weeks_listened_to=('weekNum', 'count')).reset_index()

    if not weeks_aggregated_data.empty:
        weeks_display = weeks_aggregated_data.copy()
        weeks_display['trackName'] = weeks_display['trackName'].apply(lambda s: h(s) if isinstance(s, str) else s)
        weeks_display.rename(columns={
            'trackName': h('שם שיר'),
            'weeks_listened_to': h('שבועות שנשמע')
        }, inplace=True)
        st.dataframe(weeks_display.sort_values(by=h('שבועות שנשמע'), ascending=False).head(10))

        fig, ax = plt.subplots(figsize=(8,4))
        sns.histplot(data=weeks_display, x=h('שבועות שנשמע'), bins=20, ax=ax)
        ax.set_title(h("משך זמן הופעה במצעד שבועי"))
        ax.set_xlabel(h("כמות שבועות"))
        ax.set_ylabel(h("כמות שירים"))
        st.pyplot(fig)

        top_idx = weeks_aggregated_data['weeks_listened_to'].idxmax()
        top_track = weeks_aggregated_data.loc[top_idx, 'trackName']
        top_weeks = weeks_aggregated_data.loc[top_idx, 'weeks_listened_to']
        st.success(h("🏆 השיר שהחזיק הכי הרבה שבועות: ") + " " + h(top_track) + f" ({top_weeks} {h('שבועות')})")
    else:
        st.info(h("אין נתונים להצגת שבועות הופעה"))

    # --- ניתוח פלייליסטים ---
    st.header(h("📂 ניתוח פלייליסטים"))
    playlist_file = "Playlist1.json"
    if os.path.exists(playlist_file):
        with open(playlist_file, "r", encoding="utf-8") as file:
            playlist_json = json.load(file)

        playlist_data = []
        for playlist in playlist_json.get("playlists", []):
            playlist_name_raw = playlist.get("name", "לא ידוע")
            playlist_name = h(playlist_name_raw) if isinstance(playlist_name_raw, str) else playlist_name_raw
            items = playlist.get("items", [])
            for item in items:
                track = item.get("track", {})
                track_name_raw = track.get("trackName", "")
                artist_name_raw = track.get("artistName", "")
                playlist_data.append({
                    h("שם פלייליסט"): playlist_name,
                    h("שם שיר"): h(track_name_raw) if isinstance(track_name_raw, str) else track_name_raw,
                    h("שם אמן"): h(artist_name_raw) if isinstance(artist_name_raw, str) else artist_name_raw,
                })

        if playlist_data:
            pl_df = pd.DataFrame(playlist_data)
            st.dataframe(pl_df.head(20))

            # כמה פעמים שיר מופיע בפלייליסטים
            agg = pl_df.groupby(h("שם שיר")).size().reset_index(name=h("כמות הופעות")).sort_values(by=h("כמות הופעות"), ascending=False)
            st.subheader(h("🎼 השירים הכי פופולריים בפלייליסטים"))
            st.dataframe(agg.head(10))

            fig, ax = plt.subplots(figsize=(8,4))
            top10 = agg.head(10)
            sns.barplot(data=top10, x=h("כמות הופעות"), y=h("שם שיר"), ax=ax)
            ax.set_title(h("השירים המובילים בפלייליסטים"))
            st.pyplot(fig)

            top_song_name = top10.iloc[0][h("שם שיר")]
            top_song_count = int(top10.iloc[0][h("כמות הופעות")])
            st.info(h("⭐️ השיר שמופיע הכי הרבה בפלייליסטים הוא ") + " " + top_song_name + f" ({top_song_count} {h('הופעות')})")
        else:
            st.info(h("לא נמצאו פריטי פלייליסט בתוך הקובץ"))
    else:
        st.warning(h("⚠️ לא נמצא קובץ Playlist1.json"))

else:
    st.info(h("אין נתונים להצגה — ודא שקיימים קבצי JSON בתיקיית הקלט"))
