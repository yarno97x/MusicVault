import streamlit as st
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import Database
from record import Record

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = Database()

def main():
    st.set_page_config(
        page_title="Music Database",
        page_icon="🎵",
        layout="wide"
    )
    
    st.title("🎵 Spotify Music Database")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Select Page", ["Library", "Wishlist", "Stats"])
    
    if page == "Library":
        library_page()
    elif page == "Wishlist":
        wishlist_page()
    elif page == "Stats":
        stats_page()

def library_page():
    st.header("📚 Library")
    
    # Add new album to library
    with st.expander("Add Album to Library"):
        col1, col2 = st.columns([3, 1])

        
        with col1:
            uri_input = st.text_input("Spotify Album URI", placeholder="spotify:album:...")
        
        with col2:
            rating_input = st.slider("Rating", 
                            min_value=0.0,
                            max_value=5.0,
                            step=0.5,)
        
        if st.button("Add to Library"):
            if uri_input:
                try:
                    if "http" in uri_input:
                        uri_input = "spotify:album:" + uri_input[uri_input.index("album/") + 6:uri_input.index("?")]
                    record = Record(uri_input, rating_input)
                    st.session_state.db.add_to_library(record, rating_input)
                    st.session_state.db.save()
                    st.success(f"Added '{record.name}' by {record.artist} to library!")

                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding album: {e}")
    
    # Display library
    if st.session_state.db.library:
        st.subheader(f"Your Library ({len(st.session_state.db.library)} albums)")
        
        # Sort options
        sort_by = st.selectbox("Sort by", ["Artist", "Album", "Rating"])
        
        library_list = list(st.session_state.db.library)
        if sort_by == "Artist":
            library_list.sort(key=lambda x: x.artist)
        elif sort_by == "Album":
            library_list.sort(key=lambda x: x.name)
        elif sort_by == "Rating":
            library_list.sort(key=lambda x: float(x.rated) if x.rated is not None else 0, reverse=True)
        
        # Display albums in grid
        cols = st.columns(3)
        for i, record in enumerate(library_list):
            with cols[i % 3]:
                with st.container():
                    st.image(record.img_url, width=200)
                    st.write(f"**{record.name}**")
                    st.write(f"{record.artist}")
                    if record.rated:
                        st.write(f"⭐ Rating: {record.rated}/5")
                    else:
                        st.write("⭐ Unrated")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Rate", key=f"rate_{record.uri}"):
                            st.session_state[f'rating_modal_{record.uri}'] = True
                    
                    with col2:
                        if st.button(f"Remove", key=f"remove_lib_{record.uri}"):
                            st.session_state.db.remove_from_library(record)
                            st.session_state.db.save()
                            st.rerun()
                    
                    # Rating modal
                    if st.session_state.get(f'rating_modal_{record.uri}', False):
                        new_rating = st.slider(
                            f"Rate '{record.name}'",
                            min_value=0.0,
                            max_value=5.0,
                            step=0.5,
                            key=f"rating_select_{record.uri}"
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Save Rating", key=f"save_rating_{record.uri}"):
                                record.rate(new_rating)
                                st.session_state.db.save()
                                st.session_state[f'rating_modal_{record.uri}'] = False
                                st.rerun()
                        with col2:
                            if st.button("Cancel", key=f"cancel_rating_{record.uri}"):
                                st.session_state[f'rating_modal_{record.uri}'] = False
                                st.rerun()
                    
                    st.divider()
        
        # Clear library button
        if st.button("Clear All Library", type="secondary"):
            if st.session_state.get('confirm_clear_library', False):
                st.session_state.db.clear_library()
                st.session_state.db.save()
                st.session_state.confirm_clear_library = False
                st.success("Library cleared!")
                st.rerun()
            else:
                st.session_state.confirm_clear_library = True
                st.warning("Click again to confirm clearing all library items")
    
    else:
        st.info("Your library is empty. Add some albums!")

def wishlist_page():
    st.header("⭐ Wishlist")
    
    # Add new album to wishlist
    with st.expander("Add Album to Wishlist"):
            
        uri_input = st.text_input("Spotify Album URI", placeholder="spotify:album:...")
        
        if st.button("Add to Wishlist"):
            if uri_input:
                try:
                    if "http" in uri_input:
                        uri_input = "spotify:album:" + uri_input[uri_input.index("album/") + 6:uri_input.index("?")]
                    record = Record(uri_input)
                    st.session_state.db.add_to_wishlist(record)
                    st.session_state.db.save()
                    st.success(f"Added '{record.name}' by {record.artist} to wishlist!")

                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding album: {e}")
    
    # Display wishlist
    if st.session_state.db.wishlist:
        st.subheader(f"Your Wishlist ({len(st.session_state.db.wishlist)} albums)")
        
        wishlist_list = list(st.session_state.db.wishlist)
        wishlist_list.sort(key=lambda x: x.artist)
        
        # Display albums in grid
        cols = st.columns(3)
        for i, record in enumerate(wishlist_list):
            with cols[i % 3]:
                with st.container():
                    st.image(record.img_url, width=200)
                    st.write(f"**{record.name}**")
                    st.write(f"{record.artist}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Move to Library", key=f"move_{record.uri}"):
                            st.session_state[f'move_modal_{record.uri}'] = True
                    
                    with col2:
                        if st.button(f"Remove", key=f"remove_wish_{record.uri}"):
                            st.session_state.db.remove_from_wishlist(record)
                            st.session_state.db.save()
                            st.rerun()
                    
                    # Move to library modal
                    if st.session_state.get(f'move_modal_{record.uri}', False):
                        rating = st.slider(
                            f"Rate '{record.name}'", 
                            min_value=0.0,
                            max_value=5.0,
                            step=0.5, 
                            key=f"move_rating_{record.uri}"
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Move to Library", key=f"confirm_move_{record.uri}"):
                                st.session_state.db.add_to_library(record, rating)
                                st.session_state.db.save()
                                st.session_state[f'move_modal_{record.uri}'] = False
                                st.success(f"Moved to library!")
                                st.rerun()
                        with col2:
                            if st.button("Cancel", key=f"cancel_move_{record.uri}"):
                                st.session_state[f'move_modal_{record.uri}'] = False
                                st.rerun()
                    
                    st.divider()
        
        # Clear wishlist button
        if st.button("Clear All Wishlist", type="secondary"):
            if st.session_state.get('confirm_clear_wishlist', False):
                st.session_state.db.clear_wishlist()
                st.session_state.db.save()
                st.session_state.confirm_clear_wishlist = False
                st.success("Wishlist cleared!")
                st.rerun()
            else:
                st.session_state.confirm_clear_wishlist = True
                st.warning("Click again to confirm clearing all wishlist items")
    
    else:
        st.info("Your wishlist is empty. Add some albums!")

def stats_page():
    st.header("📊 Statistics")
    
    library_count = len(st.session_state.db.library)
    wishlist_count = len(st.session_state.db.wishlist)
    
    # Overview metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Library Albums", library_count)
    
    with col2:
        st.metric("Wishlist Albums", wishlist_count)
    
    with col3:
        st.metric("Total Albums", library_count + wishlist_count)
    
    if library_count > 0:
        library_list = list(st.session_state.db.library)
        
        # Rating distribution
        st.subheader("Rating Distribution")
        rated_albums = [album for album in library_list if album.rated is not None]
        unrated_count = library_count - len(rated_albums)
        
        if rated_albums:
            ratings = [float(album.rated) for album in rated_albums]
            
            fig = px.histogram(
                x=ratings, 
                nbins=10, 
                title="Distribution of Ratings",
                labels={'x': 'Rating', 'y': 'Number of Albums'}
            )
            fig.update_xaxes(range=[0.5, 5.5])
            st.plotly_chart(fig, use_container_width=True)
            
            # Average rating
            avg_rating = sum(ratings) / len(ratings)
            st.metric("Average Rating", f"{avg_rating:.1f}/5")
            
            if unrated_count > 0:
                st.info(f"{unrated_count} albums are unrated")
        else:
            st.info("No albums have been rated yet")
        
        # Top artists
        st.subheader("Top Artists")
        artist_counts = {}
        for album in library_list:
            artist_counts[album.artist] = artist_counts.get(album.artist, 0) + 1
        
        if artist_counts:
            sorted_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            df = pd.DataFrame(sorted_artists, columns=['Artist', 'Album Count'])
            fig = px.bar(
                df, 
                x='Album Count', 
                y='Artist', 
                orientation='h',
                title="Top 10 Artists by Album Count"
            )
            fig.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig, use_container_width=True)
        
        # Highest rated albums
        if rated_albums:
            st.subheader("Highest Rated Albums")
            top_rated = sorted(rated_albums, key=lambda x: x.rated, reverse=True)[:10]
            first_col = top_rated[:5]
            sec_col = top_rated[5:10]
            
            for i, album in enumerate(first_col, 1):
                col1, col2, col3, col4 = st.columns([1, 4, 1, 4])
                with col1:
                    st.image(album.img_url, width=100)
                with col2:
                    st.write(f"**#{i}. {album.name}**")
                    st.write(f"by {album.artist}")
                    st.write(f"⭐ {album.rated:.1f}/5")
                with col3:
                    st.image(sec_col[i-1].img_url, width=100)
                with col4:
                    st.write(f"**#{i + 5}. {sec_col[i-1].name}**")
                    st.write(f"by {sec_col[i-1].artist}")
                    st.write(f"⭐ {sec_col[i-1].rated:.1f}/5")
    
    else:
        st.info("Add some albums to your library to see statistics!")

if __name__ == "__main__":
    main()
