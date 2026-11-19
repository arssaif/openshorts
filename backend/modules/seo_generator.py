"""
SEO & Social Metadata Generator:
Creates high-ranking, platform-specific metadata (titles, descriptions, hashtags, search tags)
optimized for Instagram Reels, YouTube Shorts, TikTok, and Rumble algorithms.
"""
from typing import Dict, Any, List

class SEOGenerator:
    def __init__(self):
        pass

    def generate_all_metadata(
        self,
        video_title: str,
        clip_index: int,
        hook_text: str,
        score: float,
        reasons: List[str]
    ) -> Dict[str, Any]:
        """
        Generates platform-specific SEO assets for a single clip.
        """
        clean_title = video_title.replace("GTA 6", "").replace("GTA VI", "").replace("Trailer", "").strip(" -|:")
        if not clean_title:
            clean_title = "Secret Gameplay Reveal"

        # 1. YouTube Shorts Metadata
        yt_titles = [
            f"GTA 6 Did WHAT?! 🤯 ({clean_title}) #shorts",
            f"This GTA 6 Scene Is INSANE! 🔥 #shorts",
            f"Wait for the end in GTA 6... 💀 #shorts",
            f"Rockstar cooked with this GTA 6 moment! 🚗💨 #shorts"
        ]
        yt_title = yt_titles[clip_index % len(yt_titles)]

        yt_description = f"""🔥 Watch this crazy GTA 6 moment! {hook_text}

Drop a LIKE and SUBSCRIBE if you're hyped for Grand Theft Auto VI in Vice City! 🌴☀️

🎮 Game: Grand Theft Auto VI (Rockstar Games)
🕹️ Platform: PS5, Xbox Series X/S, PC
📈 Virality Peak: {score}% Action Density

#GTA6 #GrandTheftAuto6 #GTA6Clips #GamingShorts #RockstarGames #ViceCity #GTA6Trailer #Shorts
"""
        yt_tags = [
            "gta 6", "grand theft auto 6", "gta vi", "gta 6 gameplay", "gta 6 clips",
            "gta 6 trailer", "vice city", "lucia gta 6", "jason gta 6", "rockstar games",
            "gta 6 leaks", "gta 6 graphics", "ps5 gameplay", "gaming shorts", "viral gaming"
        ]

        # 2. Instagram Reels Metadata
        ig_caption = f"""Wait until you notice this in GTA 6… 🤯🌴

"{hook_text}"

Rockstar Games is taking Vice City to a whole new level of realism and chaos! Which detail was your favorite? 👇 Drop your thoughts below!

⚡ Follow for daily GTA 6 leaks, updates & viral gameplay clips!
.
.
#GTA6 #GrandTheftAuto #RockstarGames #ViceCity #GTA6News #GTAV #GamingReels #GTA6Trailer #GamerLife #PlayStation5 #XboxSeriesX #GamingCommunity #GTAOnline #Leonida #GamingMemes #GTA6Leakes #ViceCityVibes #NextGenGaming #GamerGram #InstaGaming
"""

        # 3. TikTok Metadata
        tiktok_caption = f"Bro GTA 6 graphics look unreal 😭💀 Wait for it... #{' '.join(['gta6', 'gaming', 'grandtheftauto', 'rockstargames', 'fyp', 'viral'])}"

        # 4. Rumble Metadata
        rumble_title = f"GTA 6 Insane Scene & Gameplay Highlight - {clean_title}"
        rumble_description = f"""High-energy GTA 6 gameplay sequence featuring: {hook_text}.
Recorded and reframed in full 60FPS vertical format.
Check out more GTA 6 updates and gameplay highlights on our channel!"""
        rumble_tags = "gta6, grand theft auto 6, gaming, vice city, rockstar games, video games, gta vi clips"

        return {
            "youtube": {
                "title": yt_title,
                "description": yt_description.strip(),
                "tags": ", ".join(yt_tags),
                "tag_list": yt_tags
            },
            "instagram": {
                "caption": ig_caption.strip(),
                "hook": hook_text,
                "hashtags_count": 20
            },
            "tiktok": {
                "caption": tiktok_caption,
                "sound_tip": "Use trending GTA Vice City synthwave or rap audio for 3x algorithmic reach."
            },
            "rumble": {
                "title": rumble_title,
                "description": rumble_description.strip(),
                "tags": rumble_tags
            }
        }

