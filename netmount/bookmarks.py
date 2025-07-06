import os
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom
from netmount.config import XBEL_FILE, BOOKMARK_NS
from netmount.utils.xml_utils import prettify

ET.register_namespace("bookmark", BOOKMARK_NS)

def add_place(title, path, icon="folder", category="mounts"):
    full_title = "MNT-" + title
    if not os.path.exists(XBEL_FILE):
        root = ET.Element("xbel", version="1.0")
        tree = ET.ElementTree(root)
    else:
        tree = ET.parse(XBEL_FILE)
        root = tree.getroot()

    for bookmark in root.findall("bookmark"):
        if bookmark.find("title") is not None and bookmark.find("title").text == full_title:
            return

    unique_id = f"{int(time.time())}/0"
    bm = ET.Element("bookmark", href=f"file://{path}")
    ET.SubElement(bm, "title").text = full_title
    info = ET.SubElement(bm, "info")
    metadata = ET.SubElement(info, "metadata", owner="http://freedesktop.org")
    ET.SubElement(metadata, f"{{{BOOKMARK_NS}}}icon", name=icon)
    metadata_kde = ET.SubElement(info, "metadata", owner="http://www.kde.org")
    ET.SubElement(metadata_kde, "ID").text = unique_id
    ET.SubElement(metadata_kde, "isSystemItem").text = "false"
    ET.SubElement(bm, f"{{{BOOKMARK_NS}}}category").text = category
    ET.SubElement(bm, f"{{{BOOKMARK_NS}}}position").text = "0"

    root.append(bm)
    pretty_xml = prettify(root)

    with open(XBEL_FILE, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

def remove_place(title):
    if not os.path.exists(XBEL_FILE):
        return

    full_title = "MNT-" + title
    tree = ET.parse(XBEL_FILE)
    root = tree.getroot()
    for bookmark in root.findall("bookmark"):
        title_el = bookmark.find("title")
        if title_el is not None and title_el.text == full_title:
            root.remove(bookmark)
            break

    tree.write(XBEL_FILE, encoding="utf-8", xml_declaration=True)

def clean_mount_bookmarks():
    if not os.path.exists(XBEL_FILE):
        return

    try:
        tree = ET.parse(XBEL_FILE)
        root = tree.getroot()
        for bm in list(root.findall("bookmark")):
            title = bm.find("title")
            if title is not None and title.text.startswith("MNT-"):
                href = bm.attrib.get("href", "")
                if href.startswith("file://"):
                    real_path = href.replace("file://", "")
                    if os.path.ismount(real_path):
                        continue
                root.remove(bm)

        tree.write(XBEL_FILE, encoding="utf-8", xml_declaration=True)
    except Exception:
        pass
