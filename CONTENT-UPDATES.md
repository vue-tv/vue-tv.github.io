# VUE content updates

This repository is the source of truth for VUE wallpaper updates. There is intentionally no public admin panel: the site is public, and a public write surface would let strangers change every user's TV. The owner can ask Codex to add or replace approved backgrounds; Codex edits `content-feed.json`, runs `python3 build_content_feed.py`, and publishes the exact site source revision.

Compatible VUE clients check `content.js` on startup, when connectivity returns, and every six hours. The feed only accepts same-site image paths from the approved wallpaper set. It does not carry JavaScript, CSS, arbitrary commands, or app code. A new background appears without installing another APK/IPK once a device has the compatible content-feed client.

## Compatibility boundary

The Android APKs currently published before this integration do not contain the content-feed reader. Those installs need one compatible VUE app update before remote wallpaper updates can reach them. Android requires the user to confirm installing a new APK; VUE cannot silently replace its own app. webOS likewise needs a package containing the reader before it can receive future content. Samsung Tizen has no VUE package yet.

App features and code continue to use signed app packages. This feed is for wallpaper/content changes only.
