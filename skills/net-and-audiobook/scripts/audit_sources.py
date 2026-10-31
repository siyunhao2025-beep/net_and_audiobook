#!/usr/bin/env python3
"""Inventory every source entry and record the inspection mode; never execute inputs."""
from __future__ import annotations
import argparse,collections,hashlib,json,mimetypes,os,re,shutil,subprocess,sys,time,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TEXT_EXT={".html",".htm",".js",".mjs",".cjs",".css",".json",".jsonl",".md",".txt",".py",".ps1",".bat",".cmd",".sh",".yml",".yaml",".toml",".ini",".cfg",".csv",".tsv",".xml",".svg",".tex",".bib",".webmanifest",".map",".srt",".vtt"}
TEXT_NAMES={"LICENSE","NOTICE","README",".gitignore",".gitattributes",".env","config"}
AUDIO_EXT={".mp3",".wav",".flac",".ogg",".m4a",".aac"}
IMAGE_EXT={".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".ico"}
MODEL_EXT={".pt",".pth",".onnx",".npz",".npy",".safetensors",".bin",".pkl",".pickle"}
def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode()
    tmp=path.with_suffix(path.suffix+".tmp");tmp.write_bytes(data)
    try:os.replace(tmp,path)
    except PermissionError:
        with path.open("r+b" if path.exists() else "wb") as f:f.seek(0);f.write(data);f.truncate()
        assert path.read_bytes()==data;tmp.unlink(missing_ok=True)
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()
def redact(text):
    counts=collections.Counter()
    rules=[("private_key",r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----"),("access_token",r"\b(?:github_pat_[A-Za-z0-9_]{15,}|gh[pousr]_[A-Za-z0-9]{15,}|sk-[A-Za-z0-9_-]{15,}|hf_[A-Za-z0-9]{15,}|AKIA[A-Z0-9]{16})\b"),("email",r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),("user_home",r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"']+|/Users/[^/\s\"']+|/home/[^/\s\"']+)")]
    for name,pattern in rules:
        def sub(m,n=name):counts[n]+=1;return "<REDACTED_"+n.upper()+">"
        text=re.sub(pattern,sub,text)
    pattern=r"(?i)([\"']?(?:api[_-]?key|password|secret|access[_-]?token|refresh[_-]?token|token)[\"']?\s*[:=]\s*)([\"'])([^\r\n]*?)\2"
    def assigned(m):counts["credential_assignment"]+=1;return m[1]+m[2]+"<REDACTED>"+m[2]
    return re.sub(pattern,assigned,text),dict(counts)
def decode_text(data):
    encs=["utf-8-sig","utf-16"] if data.startswith((b"\xff\xfe",b"\xfe\xff")) else ["utf-8-sig","gb18030"]
    for encoding in encs:
        try:return data.decode(encoding),encoding
        except UnicodeError:pass
    raise UnicodeError("not decoded as supported text")
def extract_pdf(path):
    import pymupdf as fitz
    pages=[];parts=[]
    with fitz.open(path) as doc:
        for i,page in enumerate(doc):
            text=page.get_text("text",sort=True)
            pages.append({"page":i+1,"chars":len(text),"images":len(page.get_images()),"visual_review_needed":len(text.strip())<80 or bool(page.get_images())})
            parts.append(f"\n===== PAGE {i+1} =====\n"+text)
    return "\n".join(parts),{"mode":"pdf_all_pages_text_and_image_inventory","pages":pages,"page_count":len(pages),"visual_review_not_claimed":True}
def extract_office(path):
    parts=[];members=[]
    with zipfile.ZipFile(path) as z:
        if path.suffix.lower()==".pptx":
            selected=[n for n in z.namelist() if re.fullmatch(r"ppt/(?:slides/slide|notesSlides/notesSlide)\d+\.xml",n)]
            selected.sort(key=lambda n:("notesSlides" in n,int(re.search(r"(\d+)\.xml$",n)[1])))
        elif path.suffix.lower()==".docx":selected=[n for n in z.namelist() if re.fullmatch(r"word/(?:document|footnotes|endnotes|header\d+|footer\d+)\.xml",n)]
        else:selected=[n for n in z.namelist() if n in ["xl/workbook.xml","xl/sharedStrings.xml"] or re.fullmatch(r"xl/worksheets/sheet\d+\.xml",n)]
        for name in selected:
            root=ET.fromstring(z.read(name));text="\n".join(e.text for e in root.iter() if e.tag.rsplit("}",1)[-1] in ["t","v"] and e.text)
            parts.append("\n===== "+name+" =====\n"+text);members.append({"part":name,"chars":len(text)})
    return "\n".join(parts),{"mode":"office_xml_text_and_notes","parts":members,"visual_review_not_claimed":True}
def inspect_audio(path,full_decode):
    if not shutil.which("ffprobe"):return {"mode":"audio_checksum_only","unavailable":"ffprobe"}
    result=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_name,sample_rate,channels,width,height","-of","json",str(path)],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
    if result.returncode:raise ValueError("ffprobe: "+result.stderr[:300])
    info=json.loads(result.stdout);info["mode"]="audio_metadata"
    if full_decode and shutil.which("ffmpeg"):
        decoded=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-f","null","-"],capture_output=True,timeout=600)
        if decoded.returncode:raise ValueError("audio decode: "+decoded.stderr.decode(errors="replace")[:300])
        info["mode"]="audio_full_decode_and_metadata"
    info["semantic_listening_not_claimed"]=True
    return info
def inspect_file(path,full_audio,archive_budget):
    ext=path.suffix.lower();text=None
    if ext in TEXT_EXT or path.name in TEXT_NAMES or path.name.startswith(".env"):
        text,encoding=decode_text(path.read_bytes());info={"mode":"full_text","encoding":encoding,"chars":len(text),"lines":len(text.splitlines())}
        if ext in [".json",".webmanifest"]:
            try:
                obj=json.loads(text);info["json_root"]=type(obj).__name__
                if isinstance(obj,dict):info["keys"]=list(obj)
            except ValueError as e:info["parse_warning"]=str(e)
    elif ext==".pdf":text,info=extract_pdf(path)
    elif ext in [".pptx",".docx",".xlsx"]:text,info=extract_office(path)
    elif ext in AUDIO_EXT:info=inspect_audio(path,full_audio)
    elif ext in IMAGE_EXT:
        from PIL import Image
        with Image.open(path) as im:info={"mode":"image_decode_and_metadata","width":im.width,"height":im.height,"image_mode":im.mode,"format":im.format,"visual_semantics_not_claimed":True};im.load()
    elif ext in MODEL_EXT:
        info={"mode":"model_or_serialized_data_checksum_only","not_loaded_or_executed":True}
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:info.update(archive_members=len(z.infolist()),uncompressed_bytes=sum(x.file_size for x in z.infolist()))
    elif ext==".zip":
        with zipfile.ZipFile(path) as z:
            total=sum(x.file_size for x in z.infolist());info={"mode":"archive_directory","members":[{"path":x.filename,"bytes":x.file_size} for x in z.infolist()],"uncompressed_bytes":total}
            if total<=archive_budget:
                bad=z.testzip()
                if bad:raise ValueError("archive CRC error: "+bad)
                info["mode"]="archive_directory_and_all_member_crc"
            else:info["crc_not_run_reason"]="uncompressed_size_exceeds_budget"
    else:
        with path.open("rb") as f:header=f.read(4096)
        if b"\0" not in header:
            try:text,encoding=decode_text(path.read_bytes());info={"mode":"full_text_detected","encoding":encoding,"chars":len(text)}
            except UnicodeError:info={"mode":"binary_checksum_only"}
        else:info={"mode":"binary_checksum_only"}
    if text is not None:
        text,counts=redact(text);info["redactions"]=counts
    return info,text
def run(roots,out,full_audio=False,archive_budget=536870912):
    out=out.resolve()
    for root in roots.values():
        if out==root or out.is_relative_to(root):raise ValueError("Audit output must be outside all source roots")
    out.mkdir(parents=True,exist_ok=True);corpus=out/"corpus";corpus.mkdir(exist_ok=True)
    entries=[];errors=[];seen={};counts=collections.Counter();started=time.time()
    for label,root in roots.items():
        if not root.is_dir():raise FileNotFoundError(root)
        def walk_error(err):errors.append({"root":label,"path":str(err.filename),"error":str(err)})
        for directory,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
            base=Path(directory)
            for name in sorted(dirs):
                p=base/name;entries.append({"root":label,"path":p.relative_to(root).as_posix(),"kind":"symlink_directory" if p.is_symlink() else "directory"})
            for name in sorted(files):
                p=base/name;row={"root":label,"path":p.relative_to(root).as_posix(),"kind":"file","extension":p.suffix.lower()}
                try:
                    if p.is_symlink():row.update(kind="symlink_file",inspection={"mode":"link_not_followed"});entries.append(row);continue
                    st=p.stat();row.update(bytes=st.st_size,mtime_ns=st.st_mtime_ns,sha256=digest(p))
                    key=row["sha256"]
                    if key in seen:row.update(inspection=seen[key]["inspection"],duplicate_of=seen[key]["first"],corpus=seen[key].get("corpus"))
                    else:
                        info,text=inspect_file(p,full_audio,archive_budget);row["inspection"]=info
                        if text is not None:
                            target=corpus/(key+".txt");target.write_text(text,encoding="utf-8");row["corpus"]="corpus/"+target.name
                        seen[key]={"inspection":info,"first":{"root":label,"path":row["path"]},"corpus":row.get("corpus")}
                    row["status"]="inspected";counts[row["inspection"]["mode"]]+=1
                except Exception as e:
                    row.update(status="error",error=type(e).__name__+": "+str(e));errors.append({"root":label,"path":row["path"],"error":row["error"]})
                entries.append(row)
                if len(entries)%100==0:print("AUDIT_PROGRESS",len(entries),"entries",len(seen),"unique files",flush=True)
    files=[x for x in entries if x["kind"]=="file"]
    summary={"schema":"source-audit-v1","root_counts":{label:{"files":sum(x["kind"]=="file" and x["root"]==label for x in entries),"directories":sum(x["kind"]=="directory" and x["root"]==label for x in entries)} for label in roots},"files":len(files),"directories":sum(x["kind"]=="directory" for x in entries),"bytes":sum(x.get("bytes",0) for x in files),"unique_sha256":len(seen),"unique_texts":sum(bool(x.get("corpus")) for x in seen.values()),"inspection_modes":dict(counts),"extension_counts":dict(collections.Counter(x["extension"] for x in files)),"errors":errors,"elapsed_seconds":round(time.time()-started,2),"all_entries_accounted_for":not errors,"limits":"PDF images and model tensors are inventoried, not semantically reviewed. Text is redacted heuristically; never publish this private corpus automatically."}
    atomic_json(out/"manifest.json",{"roots":{k:str(v) for k,v in roots.items()},"entries":entries})
    atomic_json(out/"summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return summary
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--root",action="append",required=True,help="label=path; repeat for each authorized root");ap.add_argument("--out",required=True);ap.add_argument("--full-audio-decode",action="store_true");ap.add_argument("--archive-budget-mib",type=int,default=512);a=ap.parse_args()
    roots={}
    for item in a.root:
        if "=" not in item:ap.error("--root must be label=path")
        label,path=item.split("=",1)
        if not re.fullmatch(r"[A-Za-z0-9_-]+",label) or label in roots:ap.error("root labels must be unique simple identifiers")
        roots[label]=Path(path).resolve()
    result=run(roots,Path(a.out),a.full_audio_decode,a.archive_budget_mib*1048576)
    raise SystemExit(1 if result["errors"] else 0)
if __name__=="__main__":main()
