#encoding=utf8
import re, os, sys
sys.path.append("../")
import datetime, time
from coderstrip import *
from pythonx.funclib import *
from pythonx.kangxi import TranslateKangXi

__file__   = os.path.abspath(__file__)

# Paranoid text spacing in Python
# https://github.com/vinta/pangu.py

OPENFILE   = "openfile" in sys.argv
AUTOFORMAT = "format" in sys.argv
REBUILD    = "rebuild" in sys.argv
COPYRES    = "copyres" in sys.argv
CLEARIMG   = "clearimg" in sys.argv
IGNOREERR  = "ignoreerr" in sys.argv
OPENRESENT = "openresent" in sys.argv

# 名称，域名正则。
LINKTAGARRAY = (("bili",     "bilibili.com"),
                ("zhihu",    "zhihu.com"),
                ("cnblogs",  "cnblogs.com"),
                ("csdn",     "csdn.net"),
                ("github",   "github.com|github.io"),
                ("jianshu",  "jianshu.com"),
                ("wiki",     "wikipedia.org"),
                ("weixin",   "weixin.qq.com"),
                ("keqq",     "ke.qq.com"),
                ("scriptol", "scriptol.com"),
                ("khronos",  "khronos.org"),
                ("gluon",    "gluon.ai"),
               )

def getLinkTagSrc(name):
    return "{% include relref_"+name+".html %}"

def isHostIgnoreStat(hostk):
    for name, host in LINKTAGARRAY:
        if re.findall("^({})$".format(host), hostk):
            return True
        if re.findall("\\.({})$".format(host), hostk):
            return True
    for host in ("speclab.github.io",):
        if re.findall("^({})$".format(host), hostk):
            return True
        if re.findall("\\.({})$".format(host), hostk):
            return True
    return False

def readfileIglist(fpath):
    li = readfile(fpath, True, "utf8").split("\n")
    li = [i.strip().split(" #")[0].strip() for i in li if i.strip().split(" #")[0].strip()]
    li = [i.strip().split("# ")[0].strip() for i in li if i.strip().split("# ")[0].strip()]
    if not IGNOREERR:
        assert li, fpath
    return li

def backupUrlContent(fpath, url):
    for file in readfileIglist("config/mdrstrip_fileIgnore.txt"):
        if url.endswith(file):
            return
    assert not url.endswith(".exe"), url
    assert not url.endswith(".zip"), url
    # 有可能挂掉的网站，都稍微做一下备份。
    for host in readfileIglist("config/mdrstrip_hostIgnore.txt"):
        if url.startswith(host):
            return

    print(fpath, url)
    chrome = True # 可能有 js 代码，所以必须都用 Chrome 进行缓存
    chromeDialog = False
    for host in readfileIglist("config/mdrstrip_hostChrome.txt"):
        if url.startswith(host):
            chromeDialog = True
    mdname = os.path.split(fpath)[-1]
    urlhostsrc = calcHost(url)
    urlhostdir = urlhostsrc.replace(":", "/")
    urlmd5 = getmd5(url)[:8]
    invdir = isInvisibleDir(fpath)

    if mdname in ("wechatdl.md",):
        return

    ttype = ".html"
    ttype = calcType(ttype, url.split(urlhostsrc)[1])
    if ttype.endswith(".md"): # 不能是这个，否则会被 Jekyll 自动格式化。
        ttype = ".html"
    if ttype in (".action",):
        ttype = ".html"

    if ttype.endswith(".pdf"): # pdf 下载
        chrome = False

    def buildlocal(ftype):
        flocal = os.path.join("backup", mdname, urlhostdir, urlmd5 + ftype)
        if invdir:
            flocal = os.path.join("invisible", flocal)
        return flocal

    mdxfile = False
    flocal = buildlocal(ttype)
    if chrome and urlhostsrc in readfileIglist("config/mdrstrip_hostJekyll.txt"):
        mdxfile = True
        ttype = ".md" # 借用 Jekyll 格式化
        newlocal = buildlocal(ttype)
        if os.path.exists(flocal):
            os.rename(flocal, newlocal)
        flocal = newlocal
        ttype = ".html" # 太多了，严重影响速度，改回 html。
        newlocal = buildlocal(ttype)
        if os.path.exists(flocal):
            os.rename(flocal, newlocal)
        flocal = newlocal

    shotpath = flocal + SELENIUM
    fdata = querySnapCache(urlmd5)
    if fdata:
        writefile(flocal, fdata)
        fdatalocal = True
    else:
        fdata = netgetCacheLocal(url, timeout=60*60*24*1000, chrome=chrome, local=flocal, shotpath=shotpath, chromeDialog=chromeDialog)
        fdatalocal = False

    itag = bytesToString("无法访问此网站".encode("utf8"))
    itag2 = bytesToString('<div class="Qrcode-title">扫码登录</div>'.encode("utf8")) # 知乎的问题
    idata = bytesToString(fdata)
    if not url in readfileIglist("config/mdrstrip_InvalidURL.txt"):
        if idata.find("ERR_CONNECTION_TIMED_OUT") != -1 or (
                idata.find(itag) != -1 or idata.find(itag2) != -1):
            print("无法访问此网站", fpath, url)
            if not fdatalocal: os.system("pause")
            removeSnapCache(urlmd5)
            osremove(flocal)
            osremove(shotpath)
            return backupUrlContent(fpath, url)

    def addmdhead(fdata):
        xtime = formatTimeStamp(time.time())
        xurl = url
        fdata = """---
title : %(title)s
---

* TIME: %(time)s
* URL: <%(url)s>

-----

""" % { "time": xtime, "url": xurl, "title": "自动快照存档", } + fdata
        return fdata

    def ismdhead(fdata):
        return fdata and fdata.startswith("---")

    def html2md(fdata):
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        fdata = h.handle(fdata)
        return fdata

    if mdxfile:
        fdata = bytesToString(fdata, "utf8")
        if fdata.lower().find("<body") != -1 and fdata.lower().find("<html") != -1:
            fdata = html2md(fdata)
            fdata = addmdhead(fdata)
            writefile(flocal, fdata, "utf8")
        elif not ismdhead(fdata):
            fdata = addmdhead(fdata)
            writefile(flocal, fdata, "utf8")

        if urlhostsrc == "www.shadertoy.com":
            li = re.findall(r"""\r?\n\r?\n[0-9]+\r?\n\r?\n    \r?\n    \r?\n    """, fdata)
            for i in li: fdata = fdata.replace(i, "\r\n    ")
            writefile(flocal, fdata, "utf8")

    fmd5 = getFileMd5(flocal) # 大文件，错误已经铸成，改不了了。
    invdirlocal = isInvisibleDir(flocal)
    mdrstripBigfileCfg = os.path.join("invisible" if invdirlocal else ".", "config/mdrstrip_bigfiles.txt")
    if not fmd5 in readfileIglist(mdrstripBigfileCfg):
        if len(fdata) >= 1024*1000*1:
            assert False, (len(fdata) / 1024.0 / 1000.0, url)

    remote = buildlocal(".html" if mdxfile else ttype).replace("\\", "/")
    touchSnapCache(urlmd5, flocal)

    # protocol :// hostname[:port] / path / [:parameters][?query]#fragment
    remotename = url.split("?")[0].split("#")[0].split("/")[-1]
    if remotename in ("LICENSE-2.0",):
        return remote

    # 外链类型 断言...
    if not remote.split(".")[-1] in ("pdf", "html", "git", "php", "c", "phtml", "cpp", "htm", "shtm", "xml",
                                     "ipynb", "py", "asp", "shtml", "aspx", "xhtml", "txt", "mspx",):
        print(fpath, url)
        assert False, remote
    return remote

G_IMG_TAGED = set() # 图片资源等。
def tidyupImgClear():
    for key in G_IMG_TAGED:
        osremove(key)

def tidyupImgCollect(rootdir):
    def mainfile(fpath, fname, ftype):
        if fname.endswith(THUMBNAIL):
            if not os.path.exists(fpath[:-len(THUMBNAIL)]):
                osremove(fpath)
        else:
            G_IMG_TAGED.add(os.path.relpath(fpath, ".").lower())
    searchdir(rootdir, mainfile)

# 本地图片缓存路径。
def tidyupImg(imglocal, fpath, line):

    if imglocal in readfileIglist("config/mdrstrip_fakefiles.txt"):
        return line

    imgdir, imgfname = os.path.split(imglocal)
    if imgfname.find(".") == -1:
        imgfname = imgfname + ".jpg"
    imgtype = imgfname.split(".")[-1].lower()
    if imgtype == "mp4":
        ffmpegConvert(imglocal)

    if not COPYRES:
        assert os.path.exists(imglocal), fpath +"  "+ imglocal
        return line
    invdir = isInvisibleDir(fpath)
    fname = os.path.split(fpath)[-1]
    if fname.lower().endswith(".md"):
        fname = fname[:-3]
    if re.findall("^[0-9]{4}-[0-9]{2}-[0-9]{2}-", fname):
        fname = fname[:10].replace("-", "")[-6:]+"-"+fname[11:]
    if len(fname) > 32:
        fname = fname[:30]+"~"+getmd5(fname)[:2]

    tpath = os.path.join("assets", "images", fname, imgfname).lower()
    if invdir:
        tpath = os.path.join("invisible", "images", fname, imgfname).lower()

    if not os.path.exists(imglocal) and os.path.exists(tpath): # 貌似已经剪切过去了。
        copyfile(tpath, imglocal)
    while not os.path.exists(imglocal):
        print("文件不存在", imglocal)
        os.system("pause")

    iscopy = copyfile(imglocal, tpath) # 是否图片挪窝了。
    imglocalnail = imglocal + THUMBNAIL
    tpathnail = tpath + THUMBNAIL
    isnailcopy = False
    if os.path.exists(imglocalnail):
        isnailcopy = copyfile(imglocalnail, tpathnail) # 是否缩略图挪窝了。

    if os.path.abspath(imglocal) != os.path.abspath(tpath):
        G_IMG_TAGED.add(os.path.relpath(imglocal, ".").lower())
    if os.path.relpath(tpath, ".").lower() in G_IMG_TAGED:
        G_IMG_TAGED.remove(os.path.relpath(tpath, ".").lower())

    # 同样大小的小图片先占位... lazyload
    sizepath = tpath + THUMBNAIL
    from PIL import Image
    # 创建缩略图。
    if not os.path.exists(sizepath) and imgtype in ("png", "jpg", "gif", "jpeg", "webp", "bmp",):
        try:
            img = Image.open(tpath)
        except RuntimeError as ex: # could not create decoder object
            print("Image.open RuntimeError", tpath)
            raise ex
        width, height = img.size
        if width > 100:
            try:
                img = img.resize((100, round(100.0*height/width)), Image.ANTIALIAS).convert("RGB")
            except OSError as ex: # broken data stream when reading image file
                print("Image.resize OSError", tpath)
                raise ex
            img = img.resize((width, height), Image.ANTIALIAS) # 恢复到原来大小，便于客户端排版。

            from PIL import ImageFont, ImageDraw # 导入模块
            draw = ImageDraw.Draw(img, "RGBA") # 修改图片
            font = ImageFont.truetype(r"assets\logos\方正楷体_GB2312.ttf", size = 20)
            draw.rectangle(((0, 0), (width, 40)), fill=(0,0,0,127))
            draw.text((10, 10), u'图片加载中, 请稍后....', fill="#ffffff", font=font)
            #img.show()
            #exit(0)

        # 小于 100K...
        img = img.convert("RGB") #.convert("L")
        img.save(sizepath)
        appendfile(sizepath, getFileMd5(tpath))

    # 检查缩略图。
    elif os.path.exists(sizepath):

        srcmd5 = readfile(sizepath, True)[-32:]
        if getFileMd5(tpath) != srcmd5: # 原图变化了。
            osremove(sizepath)
            return tidyupImg(imglocal, fpath, line)

        #img = Image.open(tpath)
        #width, height = img.size
        #try:
        #    img = Image.open(sizepath)
        #except RuntimeError as ex: # could not create decoder object
        #    print("Image.open RuntimeError", sizepath)
        #    osremove(sizepath)
        #    return tidyupImg(imglocal, fpath, line) # 存在问题，重新创建。

        #if img.size != (width, height): # 尺寸不对，重新创建。
        #    img.close()
        #    osremove(sizepath)
        #    return tidyupImg(imglocal, fpath, line)

    imgtype = imgfname.split(".")[-1].lower()
    if not imgtype in ("pdf", "png", "jpg", "gif", "jpeg", "webp", "mp4", "zip", "bmp",):
        print(imglocal, fpath, line)
        assert False, imglocal

    if iscopy: osremove(imglocal)
    if isnailcopy: osremove(imglocalnail)
    return line.replace(imglocal, tpath.replace("\\", "/"))

G_HOSTSET = {}
def collectHost(fpath, line):

    reflist = []
    linesrc = line[:]

    regex = "(?:\"/(.*?)\")|(?:'/(.*?)')"
    li = re.findall(regex, line)
    for imglocal in li:
        imglocal = "".join(imglocal)
        if imglocal.endswith("/"):
            continue
        if len(imglocal) <= 2:
            continue

        kignore = False
        for src in ("/player.bilibili.com/",
                    "source/", "blog/", "source/shader/", "assets/glslEditor-0.0.20/",
                    "images/photo.jpg",):
            if imglocal.startswith(src):
                kignore = True
        if kignore: continue

        if os.path.isdir(imglocal):
            continue

        line = tidyupImg(imglocal, fpath, line)

    regex = r"""(
                    (https?)://
                        ([a-z0-9\.-]+\.[a-z]{2,6})
                        (:[0-9]{1,4})?
                    (/[a-z0-9\&%_\./~=+:@–-]*)?
                    (\?[a-z0-9\&%_\./~=+:\[\]-]*)?
                    (#[a-z0-9\&%_\./~=:?-]*)?
                )"""

    regex = "".join(regex.split())
    li = re.findall(regex, line, re.IGNORECASE)
    if not li: return reflist, line

    for tx in li:
        url = tx[0]
        host = tx[2]
        checkz = line.split(url)
        for iline in checkz[1:]: # 检查网址的后继标记。
            checkli = ["", ")", "]", ">", " ", "*"]
            for urli in readfileIglist("config/mdrstrip_urlIgnore.txt"):
                if url.startswith(urli) and urli:
                    checkli.append(";")
                    checkli.append("\"")
                    checkli.append("\'")
            if iline[:2] in ("{{",):
                continue
            if not iline[:1] in checkli:
                print(line)
                print(url)
                assert False, checkz
        assert not url.endswith("."), fpath +" "+ url
        remote = backupUrlContent(fpath, url)
        if remote:
            reflist.append([url, remote])

        if isHostIgnoreStat(host):
            continue
        if not host in G_HOSTSET:
            G_HOSTSET[host] = 0
        G_HOSTSET[host] += 1

    xline = line[:]
    for name, host in LINKTAGARRAY:
        tak = getLinkTagSrc(name)
        xline = xline.replace(tak+"]", name+"]")
    li = re.findall("<.*?>", xline)
    for tx in li:
        xline = xline.replace(tx, "")
    for name, host in LINKTAGARRAY:
        # 视频要特别标注域名。
        li1 = re.findall(host, xline, re.IGNORECASE)
        li2 = re.findall(name+"\\]", xline, re.IGNORECASE)
        if len(li1) == len(li2):
            continue
        if xline.find("[")==-1 and xline.find("<")==-1 and xline.find("(")==-1:
            continue
        print(xline)
        print(li1)
        print(li2)
        openTextFile(fpath)
        assert False, linesrc
    return reflist, line

# 语法高亮的 tag 检查。
def loadRougifyList():
    ROUGIFY_LIST_FILE = "config/rougify_list_json.txt"
    ROUGIFY_LIST = readfileJson(ROUGIFY_LIST_FILE)
    if not ROUGIFY_LIST:
        ROUGIFY_LIST_SRC = readfile("config/rougify_list.txt", True)
        ROUGIFY_LIST = re.findall("\n([^\\s:]+):", ROUGIFY_LIST_SRC, re.MULTILINE)
        ROUGIFY_LIST2 = re.findall("\\[\\s*aliases\\s*:(.*?)\\]", ROUGIFY_LIST_SRC)
        for temp in ROUGIFY_LIST2:
            temp = temp.strip().split(",")
            for itemp in temp:
                itemp = itemp.strip()
                if not itemp: continue
                ROUGIFY_LIST.append(itemp)
        assert len(ROUGIFY_LIST) == 366, len(ROUGIFY_LIST)
        writefileJson(ROUGIFY_LIST_FILE, ROUGIFY_LIST)
        for i in ROUGIFY_LIST:
            assert re.findall("^([0-9a-z_#+-]+)$", i, re.IGNORECASE), i
    return ROUGIFY_LIST

G_CNCHAR = []
G_CSCHAR = [] # 中文符号集合
G_ENCHAR = []
G_TYPESET = set()
G_MDKEYSET = set()
SNAPSHOT_HTML = "<font class='ref_snapshot'>参考资料快照</font>"
REVIEW_REGEX  = "^<p class='reviewtip'><script type='text/javascript' src='{% include relrefx?.html url=\".*?\" %}'></script></p>$"
REVIEW_FORMAT = "<p class='reviewtip'><script type='text/javascript' src='{%% include relref.html url=\"/%s.js\" %%}'></script></p>"
REVIEW_LINE   = "<hr class='reviewline'/>"
REVIEW_JS_PATH = "%s.js"
ROUGIFY_LIST = loadRougifyList()

def removeRefs(fpath, lines):
    lineCount = len(lines)
    headIndex = -1
    for index in range(lineCount):
        i = lineCount-1 - index
        if not lines[i] or not lines[i].strip():
            continue
        if re.findall("^- \\[{}\\]\\({}\\)$".format(".*?", ".*?"), lines[i]): # \\[[0-9]+\\]
            continue
        if lines[i] == SNAPSHOT_HTML:
            headIndex = i
            break
        break

    if headIndex != -1:
        assert lines[headIndex-1] == "" or re.findall(REVIEW_REGEX, lines[headIndex-1]), "%r"%lines[headIndex-1]
        assert lines[headIndex-2] in ("-----", REVIEW_LINE), "%r"%lines[headIndex-2]
        assert lines[headIndex-3] == "", "%r"%lines[headIndex-3]
        lines = lines[:headIndex-3]
    else:
        while lines and (lines[-1] in ("", "-----", REVIEW_LINE) or
                re.findall(REVIEW_REGEX, lines[-1])):
            lines = lines[:-1]
    return lines

def appendRefs(fpath, lines):
    reflist = []

    for index, line in enumerate(lines):
        ireflist, line = collectHost(fpath, line)
        lines[index] = line
        if ireflist:
            reflist.extend(ireflist)

    invdir = isInvisibleDir(fpath)
    fpath = os.path.relpath(fpath, ".")
    frelgit = fpath
    if os.path.exists(fpath+".tempd"): # 存在加密版本。
        frelgit = fpath+".tempd"

    # 获取 md 文件的最后修改时间。
    cmdx = 'git log -n 1 --pretty=format:"%ad" --date=short -- "{}"'.format(frelgit)
    if invdir:
        cmdx = 'cd {} & git log -n 1 --pretty=format:"%ad" --date=short -- "{}"'.format(*frelgit.split("\\", 1))
    datestr = popenCmd(cmdx)
    datestr = bytesToString(datestr)
    if not datestr:
        datestr = datetime.datetime.now().date()

    if fpath.startswith("_posts\\"):
        fpath = os.path.join("blogs", fpath.split("\\")[-1])
    if invdir:
        fpath = "invisible\\reviewjs\\" + fpath[len("invisible\\"):]
    else:
        fpath = "assets\\reviewjs\\" + fpath

    reviewjs = REVIEW_JS_PATH % (fpath)
    writefile(reviewjs, """document.write("%s: review");\r\n""" % datestr)
    review = REVIEW_FORMAT % (fpath.replace("\\", "/"))
    assert re.findall(REVIEW_REGEX, review), review

    if "sortrefs: true" in lines:
        reflist = sorted(reflist, key=lambda x: x[1], reverse=False)

    if reflist:
        lines.append("")
        lines.append("")
        lines.append(REVIEW_LINE)
        lines.append(review)
        lines.append(SNAPSHOT_HTML)
        lines.append("")
        lines.append("")
        urlset = set()
        count = 0
        for url, remote in reflist:
            if url in urlset: continue
            urlset.add(url)
            count = count + 1
            from urllib.parse import unquote
            remote = "{% " + ("include relrefx.html url=\"/%s\"" % (remote,)) + " %}"
            lines.append("- [{}]({})".format(url, remote)) # count
        lines.append("")
    else:
        lines.append("")
        lines.append("")
        lines.append(REVIEW_LINE)
        lines.append(review)
        lines.append("")
    return lines

def mainfile(fpath, fname, ftype):
    fpathsrc, fnamesrc, ftypesrc = fpath, fname, ftype
    checkfilesize(fpath, fname, ftype)

    ftype = ftype.lower()
    errcnt = 0

    warnCnEnSpace    = ftype in ("md", "php", "html", "htm", "vsh", "fsh",) # 英文中文空符检查
    warnTitleSpace   = ftype in ("md",) # 标题前后空行检查
    warnIndentSpace  = ftype in ("md", "php", "scss", "vsh", "fsh",) # 缩进检查
    isMdFile         = ftype in ("md",)
    isSrcFile        = ftype in ("md", "php", "html", "htm", "js", "css", "scss", "svg", "py", "vsh", "fsh",)
    keepStripFile    = ftype in ("svg",) or fname in ("gitsrc.html",) or re.findall("^relref[a-z_]*\\.html$", fname)
    keepFileTypeList = ("rar", "zip", "pdf", "mp4",) # 中英文间隔，容易造成失误的列表。

    if fpath.find("\\winfinder\\") != -1:
        isSrcFile = isSrcFile or ftype in ("h", "cpp", "rc", "c",)

    if not isSrcFile:
        if fpath.find("\\_site\\") != -1:
            G_TYPESET.add(ftype)
        return

    if isMdFile:
        # 收集 Jekyll 头定义 key 集合。
        fdata = readfile(fpath, True).strip()
        if fdata.startswith("---"):
            kvlist = fdata.split("---")[1].strip().split("\n")
            for kv in kvlist:
                kv = kv.strip()
                key, value = kv.split(":", 1)
                key = key.strip()
                value = value.strip()
                G_MDKEYSET.add(key)

    if fpath.find("\\_site\\") != -1:
        return

    def linerstrip(line):
        if isMdFile:
            for name, host in LINKTAGARRAY:
                tak = getLinkTagSrc(name)
                # 移除多余空格
                line = line.replace("  "+tak+"]", tak+"]")
                line = line.replace(" "+tak+"]", tak+"]")
                # 格式化。
                line = line.replace(tak+"]", " "+tak+"]")
                line = line.replace(name+"]", tak+"]")
                line = line.replace("[ "+tak+"]", "["+name+" "+tak+"]")
            line = line.replace(" ——", "——").replace(" ——", "——")
            line = line.replace("—— ", "——").replace("—— ", "——")
            line = line.replace("——", " —— ")
        return line.rstrip()

    print(fpath)
    md5src = getFileMd5(fpath)
    try:
        lines = readfileLines(fpath, False, False, "utf8")
    except Exception as ex:
        openTextFile(fpath)
        raise ex
    lines = removeRefs(fpath, lines)
    lines = [linerstrip(line) for line in lines]
    lines.append("")
    lines.append("")
    while len(lines) >= 2 and not lines[-1] and not lines[-2]:
        lines = lines[:-1]
    while len(lines) >= 1 and not lines[0]:
        lines = lines[1:]

    if keepStripFile:
        while len(lines) >= 1 and not lines[-1]:
            lines = lines[:-1]

    if isMdFile:
        lines = appendRefs(fpath, lines)

    codestate = False
    chartstate = False
    for index, line in enumerate(lines):

        for kftype in keepFileTypeList:
            line = line.replace(" ."+kftype, "."+kftype)
            lines[index] = line

        preline = lines[index - 1] if index > 0 else ""
        nextline = lines[index + 1] if index < len(lines)-1 else ""

        # ```java
        # {% highlight ruby %}
        # https://github.com/rouge-ruby/rouge/wiki/List-of-supported-languages-and-lexers
        li1 = re.findall("```\\s*([0-9a-z_#+-]+)", line, re.IGNORECASE)
        li2 = re.findall("\\{%\\s*highlight\\s*([0-9a-z_#+-]+)", line, re.IGNORECASE)
        li1.extend(li2)
        for i in li1:
            if not i in ROUGIFY_LIST:
                openTextFile(fpath)
                assert False, i

        tagregex = "^\\s*[#]+\\s"
        prelinetag = re.findall(tagregex, preline)
        nextlinetag = re.findall(tagregex, nextline)
        if warnTitleSpace and not codestate:
            tagregexk = "^\\s*[#]+\\s{2,}" # md 文件标题后接的空格 只能是一个。
            assert not re.findall(tagregexk, preline), preline

        if re.findall("^\\s*[*-]+\\s", line):
            idtcnt = 2 # 如果在列表里面，缩进检查 2 个为单位。
        else:
            idtcnt = 4

        cnsign  = "‘’“”" # 中文符号
        cnregex = "\u4e00-\u9fa5" # 中文汉字
        # 统计出现的字符。
        for ch in line:
            ordch = ord(ch)
            regch = "\\u%04x"%(ordch)
            if ordch <= 0x7F or isDiacritic(ch):
                G_ENCHAR.append(ch) # 英文
                continue
            if ordch >= 0x4e00 and ordch <= 0x9fa5:
                if cnregex.find(regch) == -1:
                    cnregex += regch # 中文汉字
                if G_CNCHAR.count(ch) == 0:
                    G_CNCHAR.append(ch)
            else:
                if cnsign.find(regch) == -1:
                    cnsign += regch # 中文符号
                if G_CSCHAR.count(ch) == 0:
                    G_CSCHAR.append(ch)
        cnregexc = cnregex[:]
        cnregex += cnsign # 中文汉字符号都来起。

        # 不能出现全角的空格。
        if line.find("\xa0") != -1 and not fname in ("glslEditor.min.js",):
            print("xspace", fpath, line)
            errcnt += 1

        #liw = re.findall("[{}]+".format(cnregex,), line, re.IGNORECASE)
        #lia = re.findall("[^{}]+".format(cnregex,), line, re.IGNORECASE)

        linec = line
        for itmp in re.findall("\\$\\$.*?\\$\\$", line): # 忽略数学公式
            linec = linec.replace(itmp, "$$$$")
        for itmp in re.findall("“.*?”", line): # 忽略双引号
            linec = linec.replace(itmp, "“”")
        for itmp in re.findall("`.*?`", line): # 忽略代码部分
            linec = linec.replace(itmp, "“”")

        # 忽略特殊的 tag 标记。
        for itmp in ('"WEB前端"',):
            linec = linec.replace(itmp, "\"\"")

        # 图片 caption 不校验空格。
        linec = linec.replace('caption="', 'caption=" ')

        lix1 = re.findall("[{}][^{} *]".format(cnregex, cnregex), linec, re.IGNORECASE)
        lix2 = re.findall("[^{} *][{}]".format(cnregex, cnregex), linec, re.IGNORECASE)
        lix = []
        lix.extend(lix1)
        lix.extend(lix2)

        cnsignregex = "[{}]".format(cnsign)
        for ix in lix:
            cx, cy = ix
            # 其中一个是中文符号。
            if re.findall(cnsignregex, cy) or re.findall(cnsignregex, cx):
                continue
            if cy in "-<]~" or cx in "->[~":
                continue

            if chartstate:
                continue

            if cx in ("\"", "[") and (" "+line).count(" "+ix) == 1:
                continue
            if cy in ("\"", "]", ",") and (line+" ").count(ix+" ") == 1:
                continue

            if cx in ("(", ) and (" \\"+line).count(" \\"+ix) == 1:
                continue
            if cy in ("\\", ) and (line+") ").count(ix+") ") == 1:
                continue

            if cx in ("\"",) and ("["+line).count("["+ix) == 1:
                continue
            if cy in ("\"",) and ((line+"]").count(ix+"]") == 1 or (line+",").count(ix+",") == 1):
                continue

            tagcontinue = False
            for kftype in keepFileTypeList:
                if cy in (".",) and (line.count(ix+kftype) == 1):
                    tagcontinue = True
            if tagcontinue: continue

            if not warnCnEnSpace:
                continue

            if codestate:
                if cy in "\":" or cx in "\":":
                    continue

                if line.startswith("print ("):
                    continue

            print("[%d]"%(index+1), ix, cx, cy, "\t", line)
            errcnt += 1
            if AUTOFORMAT:
                line = line.replace(ix, cx+" "+cy)
                lines[index] = line

        # 检查中文问本里面不应该出现的英文符号。
        if isMdFile:
            lixyx = re.findall("[{}] [,()] [{}]".format(cnregex, cnregex), linec, re.IGNORECASE)
            lixyx.extend(re.findall("[{}] [,()]$".format(cnregex), linec, re.IGNORECASE))
            lixyx.extend(re.findall("[{}][,;] [{}]".format(cnregexc, cnregexc), linec, re.IGNORECASE))
            if lixyx:
                openTextFile(fpath)
                print(lixyx)
                print("中文符号问题 {}:{} \"{}\"".format(fpath, index+1, linec))
                os.system("pause")
                return mainfile(fpathsrc, fnamesrc, ftypesrc)

        fxline = "".join(line.split())
        if fxline.startswith("<divclass=\"mermaid\"") and not chartstate:
            chartstate = True
        if fxline.startswith("</div>") and chartstate:
            chartstate = False

        if fxline.startswith("{%highlight"):
            codestate = True
            continue
        if fxline.startswith("{%endhighlight%}"):
            codestate = False
            continue

        if fxline.startswith("```") and not codestate:
            codestate = True
            continue
        if fxline.startswith("```") and codestate:
            codestate = False
            continue

        # 代码规范问题，需要有空格。
        if isMdFile and (line.lower().replace("endif", "x").find("if(") != -1 or line.lower().find("while(") != -1):
            openTextFile(fpath)
            print("'if(' & 'while(' 问题 {}:{} \"{}\"".format(fpath, index+1, line))
            os.system("pause")
            return mainfile(fpathsrc, fnamesrc, ftypesrc)

        if codestate:
            continue

        if warnTitleSpace and (prelinetag or nextlinetag):
            if line:
                openTextFile(fpath)
                print("标题前后空行问题 {}:{} \"{}\"".format(fpath, index+1, line))
                os.system("pause")
                return mainfile(fpathsrc, fnamesrc, ftypesrc)

        countspace = getLeftSpaceCount(line if warnIndentSpace else line.replace("\t", " "*4))
        if countspace > 12 or countspace % idtcnt == 0:
            pass # ok
        elif warnIndentSpace:
            openTextFile(fpath)
            print("空格缩进问题 {}:{} \"{}\"".format(fpath, index+1, line))
            os.system("pause")
            return mainfile(fpathsrc, fnamesrc, ftypesrc)

    assert not codestate # 断言代码片段闭合。

    page = "\r\n".join(lines)
    while page.find("\r\n" * 3) != -1:
        page = page.replace("\r\n" * 3, "\r\n" * 2)

    page = page.replace("\r\n"+REVIEW_LINE, "\r\n"*3+REVIEW_LINE)
    codereg = "\\{\\%\\s*highlight.*?\\{\\%\\s*endhighlight\\s*\\%\\}"
    codeli1 = re.findall(codereg, page, re.MULTILINE | re.IGNORECASE | re.DOTALL)

    coderegz = "```.*?```"
    codeli1z = re.findall(coderegz, page, re.MULTILINE | re.IGNORECASE | re.DOTALL)

    if warnTitleSpace:
        page = page.replace("\r\n"*2+"### ", "\r\n"*3+"### ")
        page = page.replace("\r\n"*2+"## ",  "\r\n"*3+"## ")
        page = page.replace("\r\n"*2+"# ",   "\r\n"*3+"# ")

    # 代码里面的替换要还原。
    codeli2 = re.findall(codereg, page, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    for i in range(len(codeli1)):
        page = page.replace(codeli2[i], codeli1[i])
    # 代码里面的替换要还原。
    codeli2z = re.findall(coderegz, page, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    for i in range(len(codeli1z)):
        page = page.replace(codeli2z[i], codeli1z[i])

    # 移除康熙编码，会造成乱码。
    if not fname in ("2021-03-14-Equivalent-Unified-Ideograph.md",):
        page = TranslateKangXi(page)

    # 时间过长，如果被手工改了，这里会形成覆盖。
    md5src2 = getFileMd5(fpath)
    if md5src2 == md5src:
        writefile(fpath, page.encode("utf8"))
        return errcnt

    print("文本中途被改过了。{}".format(fpath,))
    os.system("pause")
    return mainfile(fpathsrc, fnamesrc, ftypesrc)

def viewchar(lichar, xfile, xmin, xmax):
    li = list(set("".join(lichar)))
    li.sort()
    page = ""
    minv, maxv = 1024, 0
    for index, tchar in enumerate(li):
        page += tchar
        if (index + 1) % 50 == 0:
            page += "\r\n"
        if isDiacritic(tchar):
            continue
        minv = min(minv, ord(tchar))
        maxv = max(maxv, ord(tchar))
    tempfile = os.path.join("tempdir", xfile)
    writefile(tempfile, page.encode("utf8"))

    if OPENFILE:
        openTextFile(tempfile)
    print(minv, maxv)
    print([("%04x"%ord(k), k) for k in li[:5]]),
    print([("%04x"%ord(k), k) for k in li[-5:]])
    assert xmin <= minv and maxv <= xmax

def mainfilew(fpath, fname, ftype):
    if checklog(__file__, fpath) and not REBUILD:
        # print("cached", fpath)
        return 0
    removelog(__file__, fpath)
    errcnt = mainfile(fpath, fname, ftype)
    if errcnt == 0:
        savelog(__file__, fpath)
    return errcnt

G_CHECKFSIZE_CFG = {}
def checkfilesize(fpath, fname, ftype):
    # 原图不存在了，要移除缩略图。
    if fname.endswith(THUMBNAIL):
        srcimg = fpath[:-len(THUMBNAIL)]
        if not os.path.exists(srcimg):
            osremove(fpath)
            return

    invdir = isInvisibleDir(fpath)
    mdrstripBigfileCfg = os.path.join("invisible" if invdir else ".", "config/mdrstrip_bigfiles.txt")
    fmd5 = getFileMd5(fpath)
    if not mdrstripBigfileCfg in G_CHECKFSIZE_CFG.keys():
        G_CHECKFSIZE_CFG[mdrstripBigfileCfg] = set()
    if not G_CHECKFSIZE_CFG[mdrstripBigfileCfg]:
        for ifmd5 in readfileIglist(mdrstripBigfileCfg):
            G_CHECKFSIZE_CFG[mdrstripBigfileCfg].add(ifmd5)

    if not (fmd5 in G_CHECKFSIZE_CFG[mdrstripBigfileCfg]):
        size = os.path.getsize(fpath) / 1024.0 / 1000.0 # 1000 KB
        if size >= 1.0:
            print(getFileMd5(fpath), "#", fpath, "#", "%.1f MB"%size)
            G_CHECKFSIZE_CFG[mdrstripBigfileCfg].add(fmd5)

            if ftype in ("gif",):
                from pythonx import pygrab
                pygrab.gifbuildwebp(fpath)

            if not IGNOREERR:
                openTextFile(mdrstripBigfileCfg)
                assert False, "大文件最好不要入库..."

def findPostMdFile(rootdir, fnamek):
    fpathk = fnamek
    def mainfile(fpath, fname, ftype):
        if fname == fnamek:
            nonlocal fpathk
            assert fpathk == fnamek # 没有被赋值过。
            fpathk = fpath
    searchdir(rootdir, mainfile)
    return fpathk

def checkReviewJS(jsdir, rootdir):
    def mainfile(fpath, fname, ftype):
        assert fname.endswith(".md.js"), fname
        jsfile = os.path.relpath(fpath, jsdir)
        mdfile = jsfile[:-len(".js")]
        if mdfile.startswith("blogs\\"):
            mdfile = findPostMdFile("_posts", mdfile.split("\\")[-1])
            mdfile = os.path.relpath(mdfile, rootdir)
        mdfile = os.path.join(rootdir, mdfile)
        if not os.path.exists(mdfile):
            osremove(fpath)
        elif OPENRESENT:
            jsdata = readfile(fpath, True).strip() # document.write("2021-12-06: review");
            jsy, jsm, jsd = re.findall("[0-9]+", jsdata)
            today = datetime.date.today()
            jsday = datetime.date(int(jsy), int(jsm), int(jsd))
            xday = today - jsday
            print(type(xday), xday, xday.days)
            if xday.days <= 15:
                openTextFile(mdfile)
    searchdir(jsdir, mainfile)

def main():
    print(parsePythonCmdx(__file__))
    removedirTimeout("tempdir")
    clearemptydir("tempdir")
    buildSnapCache("backup")
    buildSnapCache("invisible\\backup")
    if REBUILD or OPENRESENT:
        checkReviewJS("assets\\reviewjs", ".")
        checkReviewJS("invisible\\reviewjs", "invisible")
    if CLEARIMG:
        tidyupImgCollect("assets\\images")
        tidyupImgCollect("invisible\\images")

    CHECK_IGNORE_LIST = (
        "backup", "tempdir", "_site",
        "Debug", "Release", ".vs", "opengl-3rd", "opengles3-book", "opengles-book-samples",
        "UserDataSpider", "docs.gl",
        )
    searchdir(".", checkfilesize, ignorelist=CHECK_IGNORE_LIST)
    searchdir("backup", checkfilesize, ignorelist=CHECK_IGNORE_LIST)
    searchdir("invisible\\backup", checkfilesize, ignorelist=CHECK_IGNORE_LIST)

    searchdir(".", mainfilew, ignorelist=(
        "backup", "d2l-zh", "mathjax", "tempdir", "msgboard",
        "Debug", "Release", ".vs", "openglcpp", "opengl-3rd", "opengles3-book", "opengles-book-samples",
        "UserDataSpider", "docs.gl",
        ), reverse=True)
    if REBUILD:
        clearSnapCache()
        clearemptydir("images")
        clearemptydir("source")
        tidyupImgClear()

    global G_CSCHAR
    global G_TYPESET

    viewchar(G_CNCHAR, "cnfile.txt", 0x80, 0x7FFFFFFF)
    viewchar(G_CSCHAR, "csfile.txt", 0x80, 0x7FFFFFFF)
    viewchar(G_ENCHAR, "enfile.txt", 0x0,  0x7F)

    print(LINE_SEP_SHORT)
    G_CSCHAR = list(set(G_CSCHAR))
    G_CSCHAR.sort()
    print("".join(G_CSCHAR))
    imgset  = ("jpeg", "jpg", "png", "gif", "bmp",)
    fontset = ("eot", "ttf", "woff", "svg", "woff2", )
    codeset = ("cc", "js", "txt", "xml", "css", "mk", "lock", "zip", "makefile", "scss",)
    G_TYPESET -= set(imgset)
    G_TYPESET -= set(fontset)
    G_TYPESET -= set(codeset)
    print(G_TYPESET)
    print(G_MDKEYSET)

    hostlist = sorted(G_HOSTSET.items(), key=lambda x: x[1], reverse=True)
    print(hostlist)
    for hostx in hostlist[:10]:
        print(hostx)

if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
        workdir = sys.argv[1]
        @CwdDirRun(workdir)
        def maingo():
            main()
        maingo()
    else:
        main()
        #os.system(r"cd invisible & {} tempd.py encrypt".format(getPythonExe(),))
    print(parsePythonCmdx(__file__))
