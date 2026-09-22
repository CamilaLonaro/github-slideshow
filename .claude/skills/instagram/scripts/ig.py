#!/usr/bin/env python3
"""Instagram Graph API CLI (stdlib only).

Covers: account discovery, media listing, media/account insights,
publishing (image, video/reel, carousel, story), comments, and token
exchange/refresh. Credentials come from environment variables or a
`.env` file (see SKILL.md). Never hardcode tokens.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))
ENV_FILES = [os.path.join(SKILL_DIR, ".env"), os.path.join(REPO_ROOT, ".env")]


def load_dotenv():
    """Load KEY=VALUE lines from .env files without overriding real env."""
    for path in ENV_FILES:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


load_dotenv()

TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
USER_ID = os.environ.get("IG_USER_ID", "")
APP_ID = os.environ.get("IG_APP_ID", "")
APP_SECRET = os.environ.get("IG_APP_SECRET", "")
API_VERSION = os.environ.get("IG_API_VERSION", "v23.0")
# graph.facebook.com  -> Instagram API with Facebook Login (Page-linked account)
# graph.instagram.com -> Instagram API with Instagram Login
GRAPH_HOST = os.environ.get("IG_GRAPH_HOST", "graph.facebook.com")
BASE = f"https://{GRAPH_HOST}/{API_VERSION}"

IMAGE_METRICS = "views,reach,likes,comments,saved,shares,total_interactions"
REEL_METRICS = (
    "views,reach,likes,comments,saved,shares,total_interactions,"
    "ig_reels_avg_watch_time,ig_reels_video_view_total_time"
)
STORY_METRICS = "views,reach,replies,navigation,total_interactions"
ACCOUNT_SERIES_METRICS = "reach,follower_count"
ACCOUNT_TOTAL_METRICS = (
    "views,accounts_engaged,total_interactions,likes,comments,shares,saves,"
    "replies,profile_links_taps,follows_and_unfollows"
)


class ApiError(Exception):
    pass


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def require_token():
    if not TOKEN:
        die("IG_ACCESS_TOKEN is not set. See SKILL.md / reference/setup.md.")


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------


def request(method, path, params=None, token=None, base=None):
    params = dict(params or {})
    params = {k: v for k, v in params.items() if v is not None and v != ""}
    if token is None:
        token = TOKEN
    if token:
        params["access_token"] = token
    url = (base or BASE) + path
    data = None
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "github-slideshow-instagram-skill/1.0")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body).get("error", {})
        except json.JSONDecodeError:
            err = {}
        msg = err.get("message") or body
        detail = err.get("error_user_msg") or err.get("error_user_title")
        code = err.get("code")
        sub = err.get("error_subcode")
        parts = [f"HTTP {exc.code}", f"code={code}"]
        if sub:
            parts.append(f"subcode={sub}")
        parts.append(msg)
        if detail:
            parts.append(detail)
        raise ApiError(" | ".join(str(p) for p in parts)) from None
    except urllib.error.URLError as exc:
        raise ApiError(f"network error: {exc.reason}") from None
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {"raw": body}


def get(path, **params):
    return request("GET", path, params)


def post(path, **params):
    return request("POST", path, params)


def paginate(path, limit_total, **params):
    """Follow `paging.next` until limit_total items are collected."""
    items = []
    page = get(path, **params)
    while True:
        items.extend(page.get("data", []))
        if limit_total and len(items) >= limit_total:
            return items[:limit_total]
        nxt = page.get("paging", {}).get("next")
        if not nxt:
            return items
        req = urllib.request.Request(nxt)
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = json.loads(resp.read().decode("utf-8"))


def out(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ----------------------------------------------------------------------------
# Account
# ----------------------------------------------------------------------------


def resolve_user_id():
    """Return the IG professional account id, discovering it if needed."""
    global USER_ID
    if USER_ID:
        return USER_ID
    if GRAPH_HOST == "graph.instagram.com":
        me = get("/me", fields="user_id,username")
        USER_ID = str(me.get("user_id") or me.get("id"))
        return USER_ID
    pages = get("/me/accounts", fields="name,instagram_business_account{id,username}")
    linked = [
        p for p in pages.get("data", []) if p.get("instagram_business_account")
    ]
    if not linked:
        die(
            "No Facebook Page with a linked Instagram professional account was "
            "found for this token. Link the account or set IG_USER_ID."
        )
    if len(linked) > 1:
        names = ", ".join(
            f"{p['name']} -> @{p['instagram_business_account'].get('username')} "
            f"({p['instagram_business_account']['id']})"
            for p in linked
        )
        die(f"Several linked accounts found, set IG_USER_ID to one of: {names}")
    USER_ID = linked[0]["instagram_business_account"]["id"]
    return USER_ID


def cmd_me(args):
    require_token()
    uid = resolve_user_id()
    fields = (
        "id,username,name,biography,website,followers_count,follows_count,"
        "media_count,profile_picture_url"
    )
    out(get(f"/{uid}", fields=fields))


def cmd_accounts(args):
    require_token()
    if GRAPH_HOST == "graph.instagram.com":
        out(get("/me", fields="user_id,username,account_type"))
        return
    out(get("/me/accounts", fields="id,name,instagram_business_account{id,username}"))


def cmd_limit(args):
    require_token()
    uid = resolve_user_id()
    out(get(f"/{uid}/content_publishing_limit", fields="quota_usage,config"))


# ----------------------------------------------------------------------------
# Media
# ----------------------------------------------------------------------------

MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,thumbnail_url,"
    "permalink,timestamp,like_count,comments_count,is_comment_enabled"
)


def cmd_media(args):
    require_token()
    uid = resolve_user_id()
    items = paginate(f"/{uid}/media", args.limit, fields=MEDIA_FIELDS, limit=min(args.limit, 50))
    out(items)


def cmd_media_get(args):
    require_token()
    fields = MEDIA_FIELDS + ",username,children{id,media_type,media_url,thumbnail_url}"
    out(get(f"/{args.media_id}", fields=fields))


def default_metrics_for(media_id):
    info = get(f"/{media_id}", fields="media_type,media_product_type")
    product = info.get("media_product_type", "")
    mtype = info.get("media_type", "")
    if product == "REELS" or mtype == "VIDEO":
        return REEL_METRICS
    if product == "STORY":
        return STORY_METRICS
    return IMAGE_METRICS


def flatten_insights(data):
    result = {}
    for entry in data.get("data", []):
        name = entry.get("name")
        if "values" in entry:
            values = entry["values"]
            if len(values) == 1 and "end_time" not in values[0]:
                result[name] = values[0].get("value")
            else:
                result[name] = values
        elif "total_value" in entry:
            result[name] = entry["total_value"].get("value", entry["total_value"])
        else:
            result[name] = entry
    return result


def cmd_media_insights(args):
    require_token()
    metrics = args.metrics or default_metrics_for(args.media_id)
    params = {"metric": metrics}
    if args.breakdown:
        params["breakdown"] = args.breakdown
    data = get(f"/{args.media_id}/insights", **params)
    out(data if args.raw else flatten_insights(data))


def cmd_account_insights(args):
    require_token()
    uid = resolve_user_id()
    result = {}
    since = args.since
    until = args.until
    if args.metrics:
        params = {"metric": args.metrics, "period": args.period, "since": since, "until": until}
        if args.total:
            params["metric_type"] = "total_value"
        data = get(f"/{uid}/insights", **params)
        out(data if args.raw else flatten_insights(data))
        return
    series = get(
        f"/{uid}/insights",
        metric=ACCOUNT_SERIES_METRICS,
        period=args.period,
        since=since,
        until=until,
    )
    totals = get(
        f"/{uid}/insights",
        metric=ACCOUNT_TOTAL_METRICS,
        period="day",
        metric_type="total_value",
        since=since,
        until=until,
    )
    if args.raw:
        out({"series": series, "totals": totals})
        return
    result["series"] = flatten_insights(series)
    result["totals"] = flatten_insights(totals)
    out(result)


def cmd_report(args):
    """Quick digest: account summary + last N posts with core metrics."""
    require_token()
    uid = resolve_user_id()
    profile = get(f"/{uid}", fields="username,followers_count,media_count")
    posts = paginate(
        f"/{uid}/media",
        args.limit,
        fields="id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
        limit=min(args.limit, 50),
    )
    rows = []
    for p in posts:
        metrics = (
            REEL_METRICS
            if p.get("media_product_type") == "REELS" or p.get("media_type") == "VIDEO"
            else IMAGE_METRICS
        )
        try:
            ins = flatten_insights(get(f"/{p['id']}/insights", metric=metrics))
        except ApiError as exc:
            ins = {"error": str(exc)}
        caption = (p.get("caption") or "").replace("\n", " ")
        rows.append(
            {
                "id": p["id"],
                "date": p.get("timestamp"),
                "type": p.get("media_product_type") or p.get("media_type"),
                "caption": caption[:80],
                "permalink": p.get("permalink"),
                "likes": p.get("like_count"),
                "comments": p.get("comments_count"),
                "insights": ins,
            }
        )
    out({"account": profile, "posts": rows})


# ----------------------------------------------------------------------------
# Publishing
# ----------------------------------------------------------------------------


def wait_for_container(container_id, timeout=600, interval=5):
    """Poll a media container until it is FINISHED (needed for video)."""
    deadline = time.time() + timeout
    while True:
        info = get(f"/{container_id}", fields="status_code,status")
        status = info.get("status_code")
        if status == "FINISHED":
            return info
        if status in ("ERROR", "EXPIRED"):
            raise ApiError(f"container {container_id} {status}: {info.get('status')}")
        if time.time() > deadline:
            raise ApiError(f"container {container_id} still {status} after {timeout}s")
        print(f"  container {container_id}: {status}, waiting...", file=sys.stderr)
        time.sleep(interval)


def publish_container(uid, creation_id):
    res = post(f"/{uid}/media_publish", creation_id=creation_id)
    media_id = res.get("id")
    info = get(f"/{media_id}", fields="id,permalink,media_type,timestamp")
    return info


def cmd_publish_image(args):
    require_token()
    uid = resolve_user_id()
    params = {"image_url": args.image_url, "caption": args.caption}
    if args.location_id:
        params["location_id"] = args.location_id
    if args.user_tags:
        params["user_tags"] = args.user_tags
    if args.alt_text:
        params["alt_text"] = args.alt_text
    container = post(f"/{uid}/media", **params)
    cid = container["id"]
    if args.dry_run:
        out({"container_id": cid, "published": False})
        return
    wait_for_container(cid, timeout=120)
    out(publish_container(uid, cid))


def cmd_publish_video(args):
    require_token()
    uid = resolve_user_id()
    params = {
        "media_type": "REELS",
        "video_url": args.video_url,
        "caption": args.caption,
        "share_to_feed": "true" if args.share_to_feed else "false",
    }
    if args.cover_url:
        params["cover_url"] = args.cover_url
    if args.thumb_offset is not None:
        params["thumb_offset"] = args.thumb_offset
    if args.audio_name:
        params["audio_name"] = args.audio_name
    container = post(f"/{uid}/media", **params)
    cid = container["id"]
    wait_for_container(cid)
    if args.dry_run:
        out({"container_id": cid, "published": False})
        return
    out(publish_container(uid, cid))


def cmd_publish_carousel(args):
    require_token()
    uid = resolve_user_id()
    urls = args.items
    if not 2 <= len(urls) <= 10:
        die("a carousel needs between 2 and 10 items")
    children = []
    for url in urls:
        lower = url.lower().split("?")[0]
        if lower.endswith((".mp4", ".mov")):
            params = {"media_type": "VIDEO", "video_url": url, "is_carousel_item": "true"}
        else:
            params = {"image_url": url, "is_carousel_item": "true"}
        child = post(f"/{uid}/media", **params)
        children.append(child["id"])
        print(f"  child container {child['id']} for {url}", file=sys.stderr)
    for cid in children:
        wait_for_container(cid)
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": args.caption,
    }
    if args.location_id:
        params["location_id"] = args.location_id
    container = post(f"/{uid}/media", **params)
    cid = container["id"]
    wait_for_container(cid)
    if args.dry_run:
        out({"container_id": cid, "children": children, "published": False})
        return
    out(publish_container(uid, cid))


def cmd_publish_story(args):
    require_token()
    uid = resolve_user_id()
    params = {"media_type": "STORIES"}
    if args.image_url:
        params["image_url"] = args.image_url
    elif args.video_url:
        params["video_url"] = args.video_url
    else:
        die("provide --image-url or --video-url")
    container = post(f"/{uid}/media", **params)
    cid = container["id"]
    wait_for_container(cid)
    if args.dry_run:
        out({"container_id": cid, "published": False})
        return
    out(publish_container(uid, cid))


def cmd_publish_container(args):
    """Publish a previously created container (e.g. after --dry-run)."""
    require_token()
    uid = resolve_user_id()
    wait_for_container(args.container_id)
    out(publish_container(uid, args.container_id))


def cmd_container_status(args):
    require_token()
    out(get(f"/{args.container_id}", fields="id,status_code,status"))


def cmd_delete(args):
    require_token()
    if not args.yes:
        die("refusing to delete without --yes")
    out(request("DELETE", f"/{args.media_id}"))


# ----------------------------------------------------------------------------
# Comments
# ----------------------------------------------------------------------------


def cmd_comments(args):
    require_token()
    fields = "id,text,username,timestamp,like_count,hidden,replies{id,text,username,timestamp}"
    items = paginate(f"/{args.media_id}/comments", args.limit, fields=fields, limit=min(args.limit, 50))
    out(items)


def cmd_reply(args):
    require_token()
    out(post(f"/{args.comment_id}/replies", message=args.message))


def cmd_hide_comment(args):
    require_token()
    out(post(f"/{args.comment_id}", hide="true" if not args.unhide else "false"))


# ----------------------------------------------------------------------------
# Tokens
# ----------------------------------------------------------------------------


def cmd_token_exchange(args):
    """Turn a short-lived token into a long-lived one (about 60 days)."""
    short = args.token or TOKEN
    if not short:
        die("pass --token or set IG_ACCESS_TOKEN")
    if GRAPH_HOST == "graph.instagram.com":
        if not APP_SECRET:
            die("IG_APP_SECRET is required")
        res = request(
            "GET",
            "/access_token",
            {"grant_type": "ig_exchange_token", "client_secret": APP_SECRET, "access_token": short},
            token="",
            base="https://graph.instagram.com",
        )
    else:
        if not (APP_ID and APP_SECRET):
            die("IG_APP_ID and IG_APP_SECRET are required")
        res = request(
            "GET",
            "/oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "fb_exchange_token": short,
            },
            token="",
        )
    out(res)


def cmd_token_refresh(args):
    """Instagram Login only: refresh a long-lived token before it expires."""
    require_token()
    if GRAPH_HOST != "graph.instagram.com":
        die("token-refresh applies to Instagram Login (IG_GRAPH_HOST=graph.instagram.com). "
            "For Facebook Login, re-run token-exchange with a fresh short-lived token.")
    res = request(
        "GET",
        "/refresh_access_token",
        {"grant_type": "ig_refresh_token", "access_token": TOKEN},
        token="",
        base="https://graph.instagram.com",
    )
    out(res)


def cmd_token_debug(args):
    require_token()
    if GRAPH_HOST == "graph.instagram.com":
        out(get("/me", fields="user_id,username"))
        return
    app_token = f"{APP_ID}|{APP_SECRET}" if APP_ID and APP_SECRET else TOKEN
    res = request("GET", "/debug_token", {"input_token": TOKEN}, token=app_token)
    data = res.get("data", res)
    for key in ("expires_at", "data_access_expires_at", "issued_at"):
        if isinstance(data.get(key), int) and data[key] > 0:
            data[key + "_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(data[key]))
    out(data)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def build_parser():
    p = argparse.ArgumentParser(prog="ig.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("me", help="profile of the connected account").set_defaults(fn=cmd_me)
    sub.add_parser("accounts", help="list Pages / IG accounts the token can see").set_defaults(fn=cmd_accounts)
    sub.add_parser("limit", help="publishing quota usage (100 posts / 24h)").set_defaults(fn=cmd_limit)

    s = sub.add_parser("media", help="list recent posts")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(fn=cmd_media)

    s = sub.add_parser("media-get", help="details of one post")
    s.add_argument("media_id")
    s.set_defaults(fn=cmd_media_get)

    s = sub.add_parser("media-insights", help="metrics for one post")
    s.add_argument("media_id")
    s.add_argument("--metrics", help="comma-separated; default depends on media type")
    s.add_argument("--breakdown", help="e.g. action_type for total_interactions")
    s.add_argument("--raw", action="store_true")
    s.set_defaults(fn=cmd_media_insights)

    s = sub.add_parser("account-insights", help="account-level metrics")
    s.add_argument("--metrics", help="comma-separated; default = reach,follower_count + totals")
    s.add_argument("--period", default="day", choices=["day", "week", "days_28", "lifetime"])
    s.add_argument("--since", help="unix timestamp or YYYY-MM-DD")
    s.add_argument("--until", help="unix timestamp or YYYY-MM-DD")
    s.add_argument("--total", action="store_true", help="request metric_type=total_value")
    s.add_argument("--raw", action="store_true")
    s.set_defaults(fn=cmd_account_insights)

    s = sub.add_parser("report", help="account summary + metrics for the last N posts")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("publish-image", help="publish a single image (JPEG, public URL)")
    s.add_argument("--image-url", required=True)
    s.add_argument("--caption", default="")
    s.add_argument("--alt-text")
    s.add_argument("--location-id")
    s.add_argument("--user-tags", help='JSON list: [{"username":"x","x":0.5,"y":0.5}]')
    s.add_argument("--dry-run", action="store_true", help="create the container but do not publish")
    s.set_defaults(fn=cmd_publish_image)

    s = sub.add_parser("publish-video", help="publish a Reel (MP4/MOV, public URL)")
    s.add_argument("--video-url", required=True)
    s.add_argument("--caption", default="")
    s.add_argument("--cover-url")
    s.add_argument("--thumb-offset", type=int, help="cover frame offset in ms")
    s.add_argument("--audio-name")
    s.add_argument("--no-feed", dest="share_to_feed", action="store_false", help="do not show in the main feed")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_publish_video)

    s = sub.add_parser("publish-carousel", help="publish 2-10 images/videos as a carousel")
    s.add_argument("--caption", default="")
    s.add_argument("--location-id")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("items", nargs="+", help="public URLs, in order")
    s.set_defaults(fn=cmd_publish_carousel)

    s = sub.add_parser("publish-story", help="publish a story (image or video)")
    s.add_argument("--image-url")
    s.add_argument("--video-url")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_publish_story)

    s = sub.add_parser("publish-container", help="publish an existing container id")
    s.add_argument("container_id")
    s.set_defaults(fn=cmd_publish_container)

    s = sub.add_parser("container-status", help="processing status of a container")
    s.add_argument("container_id")
    s.set_defaults(fn=cmd_container_status)

    s = sub.add_parser("delete", help="delete a post (irreversible)")
    s.add_argument("media_id")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_delete)

    s = sub.add_parser("comments", help="list comments on a post")
    s.add_argument("media_id")
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(fn=cmd_comments)

    s = sub.add_parser("reply", help="reply to a comment")
    s.add_argument("comment_id")
    s.add_argument("message")
    s.set_defaults(fn=cmd_reply)

    s = sub.add_parser("hide-comment", help="hide (or unhide) a comment")
    s.add_argument("comment_id")
    s.add_argument("--unhide", action="store_true")
    s.set_defaults(fn=cmd_hide_comment)

    s = sub.add_parser("token-exchange", help="short-lived -> long-lived token")
    s.add_argument("--token", help="short-lived token (defaults to IG_ACCESS_TOKEN)")
    s.set_defaults(fn=cmd_token_exchange)

    sub.add_parser("token-refresh", help="refresh a long-lived token (Instagram Login)").set_defaults(fn=cmd_token_refresh)
    sub.add_parser("token-debug", help="show token scopes and expiry").set_defaults(fn=cmd_token_debug)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except ApiError as exc:
        die(str(exc))
    except KeyboardInterrupt:
        die("interrupted", 130)


if __name__ == "__main__":
    main()
