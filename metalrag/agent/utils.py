from metallum import Band, Album

def band2dict(band: Band, is_containing_albums: bool = True) -> dict[str, str]:
    return {
        "name": band.name,
        "country": band.country,
        "location": band.location,
        "status": band.status,
        "formed_in": band.formed_in,
        "genres": band.genres,
        "themes": band.themes,
        "albums": [
           album2dict(album, band_name=band.name) for album in band.albums 
        ] if is_containing_albums else None
    }
    
def album2dict(album: Album, is_containing_band: bool = False, band_name: str | None = None) -> dict[str, str]:
    return {
        "bands": [
            band2dict(band) for band in album.bands
        ] if is_containing_band else [band_name],
        "title": album.title,
        "type": album.type,
        #"year": album.year,
        #"label": album.label,
    }