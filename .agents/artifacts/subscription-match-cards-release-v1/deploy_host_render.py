"""Render synthetic subscription pages from the active private generation."""

import json
import subprocess
import sys

RENDER = r"""
import hashlib,importlib.metadata,io,json,pathlib,re,socket,sys
from datetime import UTC,datetime
def denied(*args,**kwargs):
    raise AssertionError('synthetic_render_network_blocked')
socket.socket.connect=denied
socket.socket.connect_ex=denied
socket.socket.sendto=denied
socket.getaddrinfo=denied
active_path=pathlib.Path('/gsuid_core/data/Dota2UID/runtime/active.json')
active_bytes=active_path.read_bytes()
active=json.loads(active_bytes)
assert re.fullmatch('[0-9a-f]{64}',active['manifest_sha256'])
assert re.fullmatch('[0-9a-f]{32}',active['generation'])
generation=active_path.parent/active['manifest_sha256']/active['generation']
sys.path.insert(0,str(generation))
import dota2forge_core as core
import dota2forge_renderer as rendering
from PIL import Image
assert pathlib.Path(core.__file__).resolve().is_relative_to(generation.resolve())
assert pathlib.Path(rendering.__file__).resolve().is_relative_to(generation.resolve())
assert importlib.metadata.version('dota2forge-core')=='0.1.0a7'
assert importlib.metadata.version('dota2forge-renderer')=='0.1.0a7'
assert importlib.metadata.version('pillow')=='12.3.0'
metadata=core.DataMetadata(core.DataSource.FIXTURE,datetime(2026,10,13,tzinfo=UTC))
players=tuple(core.MatchParticipant(
    player_slot=index if index<5 else 128+index-5,
    account_id=core.AccountId(2000+index),display_name=f'合成玩家 {index+1}',
    is_anonymous=False,is_radiant=index<5,hero_id=index+1,
    kills=index+2,deaths=3,assists=4,gold_per_minute=300+index*20,
    experience_per_minute=400+index*20,level=20+index,last_hits=100+index,
    denies=index,net_worth=12000+index*1000,hero_damage=15000+index*1000,
    tower_damage=1000+index*100,hero_healing=0,item_ids=(1,0,None,63,0,0),
    backpack_ids=(0,1,None),neutral_item_id=0,position=f'POSITION_{index%5+1}',
    lane='SAFE_LANE',imp=None) for index in range(10))
match_id=core.MatchId(7001)
detail=core.MatchDetail(match_id,metadata,duration_seconds=2100,did_radiant_win=False,
    game_mode='ALL_PICK_RANKED',game_version_id=190,has_stats=True,players=players)
report=core.MatchReport(match_id,metadata,core.AccountId(2002),None,detail,
    core.MatchAnalysisUnavailable(match_id,metadata))
key=core.SubscriptionKey(core.PlatformIdentity('synthetic','offline','fixture-bot','fixture-owner'),
    'group:synthetic',core.AccountId(2002),core.DataSource.FIXTURE,core.SubscriptionKind.NEW_MATCH)
event=core.SubscriptionEvent('a'*32,'b'*32,key,metadata.fetched_at,report)
cards=rendering.subscription_event_cards(event)
assert len(cards)==3
renderer=rendering.PillowRenderer()
pages=[]
try:
    for card in cards:
        artifact=renderer.render(card)
        assert artifact.width==1600 and artifact.height<=3200
        assert len(artifact.data)<=2*1024*1024
        with Image.open(io.BytesIO(artifact.data)) as decoded:
            assert decoded.format=='PNG' and decoded.size==(artifact.width,artifact.height)
        pages.append({'page':card.page,'width':artifact.width,'height':artifact.height,'bytes':len(artifact.data),'format':'PNG'})
finally:
    renderer.close()
assert active_path.read_bytes()==active_bytes
assert not any(name=='gsuid_core' or name.startswith('gsuid_core.')
    or name=='Dota2UID' or name.startswith('Dota2UID.') for name in sys.modules)
print(json.dumps({'passed':True,'synthetic_only':True,'source':'FIXTURE','active_runtime_manifest_sha256':active['manifest_sha256'],
    'runtime_versions':active['versions'],'host_pillow':'12.3.0','pages':pages,'network_blocked':True,
    'sdk_or_adapter_imported':False,'real_configuration_or_database_read':False,'provider_called':False,
    'messages_sent':False,'rendered_pngs_saved':False,'active_record_unchanged':True}))
"""


def main():
    script = RENDER + "\n"
    guarded = "try:\n" + "\n".join("    " + line for line in script.splitlines())
    guarded += "\nexcept Exception as error:\n"
    guarded += "    print(json.dumps({'passed':False,'error_category':type(error).__name__,"
    guarded += "'raw_exception_output':False}))\n"
    guarded += "    sys.exit(1)\n"
    process = subprocess.run(
        ["docker", "exec", "-i", "gscore", "/venv/bin/python", "-I", "-B", "-c", guarded],
        capture_output=True,
        text=True,
        timeout=90,
    )
    try:
        result = json.loads(process.stdout)
    except ValueError:
        result = {
            "passed": False,
            "error_category": "host_render_result_unavailable",
            "raw_exception_output": False,
        }
    print(json.dumps(result, indent=2))
    sys.exit(process.returncode)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            json.dumps(
                {
                    "passed": False,
                    "error_category": type(error).__name__,
                    "raw_exception_output": False,
                }
            )
        )
        sys.exit(1)
