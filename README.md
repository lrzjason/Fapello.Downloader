## Thanks for Djdefrag open source this downloader
Based on the original repo, I've added a few functionality to make it more useful for me.
- Moved all downloads to output folder
- Added gitignore
- allow to download by model name, e.g. mia-kha***
- support multiple models at once, e.g. model-a***, model-b***, model-c***
- support auto retry
- support files verify, download the same model without duplicated download
- added run.bat for windows


## The following is the original repo Readme

<div align="center">
    <br>
    <img src="https://user-images.githubusercontent.com/32263112/205343453-e2f61261-3fb4-4d9b-8fe7-2be67fc0fcfb.png" width="175"> </a> 
    <br><br> Fapello.Downloader - NSFW images/videos downloader app <br><br>
    <a href="https://jangystudio.itch.io/fapellodownloader">
        <button>
            <img src="https://static.itch.io/images/badge-color.svg" width="225" height="70">
        </button>     
    </a>
</div>
<br>
<div align="center">
    <img src="https://github.com/user-attachments/assets/7a981b8e-8769-4548-8faa-3b14ac5fd373"> </a> 
</div>

## Other projects.🤓

- https://github.com/Djdefrag/QualityScaler / QualityScaler - image/video AI upscaler
- https://github.com/Djdefrag/RealScaler / RealScaler -  image/video AI upscaler app (Real-ESRGAN)
- https://github.com/Djdefrag/FluidFrames.RIFE / FluidFrames.RIFE - video AI frame generation


## How is made. 🛠

Fapello.Downloader is completely written in Python, from backend to frontend. External packages are:
- [ ] Core -> beautifulsoup / requests
- [ ] GUI -> customtkinter
- [ ] Packaging -> pyinstaller

## How to use. 👨‍💻
* Copy the Fapello link of interest (for example: https://fapello.com/mia-kha***/)
* Paste the copied link in FapelloDownloader textbox
* Press Download button
* Wait for the download to complete
* A folder will be created with all images/videos

## Next steps. 🤫
- [ ] Update libraries 
    - [x] Python 3.10 (expecting ~10% more performance) 
    - [x] Python 3.11 (expecting ~30% more performance)

