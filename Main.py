import os
import cv2
import flet as ft
from Database import Database, FISH_IMAGE_DIR
from PIL import Image
import numpy as np
import io

import base64

from fish_classifier import detect_fish_from_bytes


db = Database()

#-----------SCAN BUTTON AND FISH INFO DISPLAY-----------

#This is where the fish info will be displayed after the image is uploaded and processed. Like we get info from 
# scanning the fish and then it appends to here to show the text.

fish_info = ft.Column()

def image_to_base64(path):
    with open(path, "rb") as img_file:
        img_bytes = img_file.read()
    encoded = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"

def bytes_to_image(image_bytes: bytes) -> np.ndarray:
    img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    return img_cv

def load_collection_ui() -> ft.Column:
    controls = []

    for fish in db.get_collection():
        img_path = os.path.join(FISH_IMAGE_DIR, fish["filename"])
        img_src = image_to_base64(img_path)
        fish_display = ft.Container(
            ft. Column([
                ft.Image(src=img_src, width=150, height=150, fit='contain'),
                ft.Text(f"Species: {fish['label']}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE),
                ft.Text(f"Confidence: {fish['confidence']*100:.1f}%", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                ft.Text(f"Habitat: {fish.get('habitat', 'N/A')}", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                ft.Text(f"Region: {fish.get('ocean_region', 'N/A')}", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
            ], spacing=5),
            padding =10,
            margin = 5,
            border_radius = 10,
            bgcolor = ft.Colors.BLUE_100,
            width = 180,
        )
        controls.append(fish_display)

    return ft.Column([ft.Row(controls, wrap=True, alignment=ft.MainAxisAlignment.START),],scroll="auto", expand=True)

async def scan_click(event: ft.ControlEvent):
    #is the file picker, lets user choose a file from computer
    file_picker = ft.FilePicker()


    # calls filepicker, and waits for user to select file before proceeding.
    files = await file_picker.pick_files(with_data=True, allow_multiple=False)
    if not files:
        return

    picked = files[0]

    nparr = np.frombuffer(picked.bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Call the fish detection function and uses the image bytes from picked file as the parameter.
    result = detect_fish_from_bytes(picked.bytes)

    # this'll convert the bytes to a cv2, which the Db can use.
    frame = bytes_to_image(picked.bytes)

    detection = {
        "label": result["species"],
        "confidence": result["confidence"],
        "bbox": None
    }

    save_info = db.save_fish(frame, detection, habitat=result["habitat"], ocean_region=result["ocean_region"])

    fish_info.controls.clear()
    fish_info.controls.append(
        ft.Text(
            f"Species: {result['species']}\n"
            f"Confidence: {result['confidence']*100:.1f}%\n"
            f"Habitat: {result['habitat']}\n"
            f"Region: {result['ocean_region']}"
        )
    )
    fish_info.update()

    page = event.page
    def _close(_event):
        if page.dialog:
            page.dialog.open = False
            page.dialog = None
            page.update()
    #Idk why this is not working. it should work.
    dialog = ft.AlertDialog(
        title=Popup_header,
        content=ft.Column(
            controls=[
            ft.Text("Your fish's properties:"),
            ft.Divider(height=20),
            ft.Text(f"Species: {result['species']}"),
            ft.Text(f"Confidence: {result['confidence']*100:.1f}%"),
            ft.Text(f"Habitat: {result['habitat']}"),
            ft.Text(f"Region: {result['ocean_region']}"),
            ]
        ),
        actions=[ft.TextButton("Close", on_click=_close)],
    )

    page.dialog = dialog
    
    dialog.open = True
    page.update()

scan_button = ft.Button(
    "Scan",
    on_click=scan_click,
)

#-------------------------The Different Pages------------------------------------

Popup_header = ft.Row(
    ft.Text(
        "Scan Results",
        size=50,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )
) 

scan_popup = ft.Column(
            controls=[
                Popup_header,
                ft.Divider(height=20),
                ft.Text("Your fish's properties:"),
                fish_info
            ]
                )

scan_page = ft.Container(
    ft.Column( 
        [
        ft.Text(
            "Fish Properties",
            size=25,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.ORANGE,
            ),
        scan_button,
        fish_info
        ]
    )
)

collection_page = ft.Container()

reward_page = ft.Container(
    ft.Column(
        [
            ft.Text(
                "Reward Page",
                size=25,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.ORANGE,
            )
        ]
    )
)

profile_page = ft.Container(
    ft.Column(
        [
            ft.Text(
                "Profile Page",
                size=25,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.ORANGE,
            ),
            ft.Text(
                "Username: FishLover123\n"
                "Points: 150\n"
                "Badges: Salmon Slayer, Trout Tracker",
                size=16,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.WHITE,
            )
        ]

    )
)

#------------------------------PAGE SETUP------------------------------

# result = detect_fish_from_bytes(b"fake bytes")

def main(page: ft.Page):
    page.title = "Fish Discount App"
    page.theme_mode = ft.ThemeMode.DARK
    #page.add(scan_page, ft.Divider(height=20),  scan_button, ft.Divider(height=20), fish_info)

    content = ft.Container(expand=True, content=scan_page)

    rail = ft.NavigationRail(
        selected_index=0,
        expand=True,
        extended=True,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=60,
        min_extended_width=200,

        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.CAMERA_ALT,label="Scan"),
            ft.NavigationRailDestination(icon=ft.Icons.SET_MEAL, label="Collection"),
            ft.NavigationRailDestination(icon=ft.Icons.QR_CODE,label="Rewards"),
            ft.NavigationRailDestination(icon=ft.Icons.PERSON,label="Profile"),
        ],
        on_change=lambda event: change_page(event, content)
    )

    toggle_button = ft.IconButton(
        icon=ft.Icons.MENU,
        on_click=lambda event: toggle_sidebar(rail)
    )

    sidebar = ft.Column(
        [
            toggle_button,
            rail
        ],
    )

    page.add(
        ft.Row(
            [
                sidebar,
                ft.VerticalDivider(width=1),
                content
            ],
            expand=True
        )
    )


#------------------------------
def change_page(event: ft.ControlEvent, content: ft.Container):
    index = event.control.selected_index
    if index == 0:
        content.content = scan_page
    elif index == 1:
        content.content = ft.Container(content=load_collection_ui(), padding=10)
    elif index == 2:
        content.content = reward_page
    elif index == 3:
        content.content = profile_page
    content.update()

def toggle_sidebar(rail: ft.NavigationRail):
    if rail.extended == True:
        rail.extended = False
    else:
        rail.extended = True
    rail.update()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=8550)

# create a pop up kind of box, for when you finish scanning.