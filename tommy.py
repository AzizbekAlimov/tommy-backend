"""
TOMMY BOT — Complete + ULTRA MODERATION v3
Swear, Ads, Links, Bad Stickers, Bad GIFs -> 5 Warnings -> 1h Mute
"""
import os, io, re, json, time, sqlite3, asyncio, logging, threading
from io import BytesIO
from datetime import datetime, timezone, timedelta

from PIL import Image
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, BotCommand,
    BotCommandScopeChatAdministrators,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
    ChatMemberHandler
)
from telegram.request import HTTPXRequest

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ============================================================
# SETTINGS
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@TommyXcheat2")
OWNER_FIXED = "@Tommy_1727"
ADMIN_ID = 7383782449
PORT = int(os.getenv("PORT", 3000))
TZ_TASHKENT = timezone(timedelta(hours=5))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_VISION_AVAILABLE = False
if GEMINI_AVAILABLE and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_VISION_AVAILABLE = True
    logger.info("✅ Gemini AI (Vision) connected")

PHOTO, PLAYER_ID, CLASSIC, ULTIMATE, KILLS = range(5)

# ============================================================
# 500+ SO'KINISHLAR (BAD WORDS)
# ============================================================
BAD_WORDS = [
    # O'ZBEKCHA
    "ahmoq","tentak","qo'tir","harom","jinni","esingni","yedingmi","onang","otang",
    "jalab","qang'ir","sikin","sik","kot","jalap","qotoq","qo'toq","yaramas","pastkash",
    "razil","fohisha","qanjiq","it","itvachcha","eshak","cho'chqa","domla","sassiq",
    "badbaxt","bevafo","siktir","gandon","gandonvachcha","jalapvachcha","qotoqvachcha",
    "haromzoda","haromi","tentakvachcha","ahmoqvachcha","siktirib","sikib","sikaman",
    "sikasan","sikadi","sikdik","qotoqni","am","ami","amingni","aming","amini","kotni",
    "kotingni","koting","kotini","jalabni","onangni","otangni","singlingni","opangni",
    "gandonni","yaramasvachcha","najot","najos","najosat","iflos","iflosvachcha","hayvon",
    "hayvonvachcha","mol","molvachcha","qanjiqvachcha","qanjiqni","qanjiqning",
    "fohishavachcha","fohishani","pastkashvachcha","razilvachcha","sharmanda","beodob",
    "tarbiyasiz","qo'pol","besharm","uyatsiz","sassiqvachcha","badbo'y","ablah","tuban",
    "qabih","yaramassan","yaramassiz","sikdiring","sikiling","sikilsin","qotoqingni",
    "qotoqing","dalbayob","tentaklar","ahmoqlar","jinnilar","qotoqchalar","qanjiqlar",
    "fohishalar","razilchalar","siktiribyubor","onangni","otangni",
    # RUSCHA
    "блядь","бля","блять","блядина","блядство","блядский","сука","суки","сук","сукин",
    "сучара","сучка","сучки","хуй","хуя","хую","хуём","хуи","хуёвый","хуёво","хуйня",
    "хуйло","хуёк","хуячить","хуярит","пизда","пизды","пизде","пизду","пиздой","пиздец",
    "пиздато","пиздёнка","пиздюк","пиздобол","ебать","ебал","ебала","ебёт","ебет","ебут",
    "ебись","еби","ебанный","ебанутый","ебаный","ёбаный","ебало","ебло","ебальник",
    "ебашит","ебашил","ебался","ебалась","мудак","мудаки","мудила","мудилы","мудило",
    "мудил","гандон","гандоны","гандонский","пидор","пидорас","пидорасы","пидр","пидоры",
    "пидорасня","пидорский","пидораска","пидорок","залупа","залупы","залупе","залупу",
    "залупой","залупка","долбоёб","долбоеб","долбоёбы","долбоебы","долбоёбка","уёбок",
    "уебок","уёбки","уебки","уёбище","уебище","уёбищный","нахуй","нахуя","нахуйня",
    "нахуйник","нихуя","нихуй","похуй","похуя","похуист","охуеть","охуел","охуела",
    "охуели","охуенный","охуенно","охуительный","охуительно","охуевший","говно","говна",
    "говне","говну","говном","говнюк","говнюки","говнючка","говняный","говняно","говнище",
    "говнистый","дерьмо","дерьма","дерьме","дерьму","дерьмом","дерьмовый","жопа","жопы",
    "жопе","жопу","жопой","жопка","жопный","жополиз","жополизы","жополизка","срать",
    "срал","срала","срали","сру","срака","сраки","сракер","сраный","сраная","срань",
    "срач","срачи","ссать","ссал","ссала","ссали","ссу","ссыкун","ссыкуха","ссыкло",
    "ссыкливый","ссыкуня","мразь","мрази","мразью","мразей","мразота","мразотный","тварь",
    "твари","тварью","тварей","тварьё","тварюга","скотина","скотины","скотине","скотину",
    "скотиной","скотиняка","сволочь","сволочи","сволочью","сволочей","сволочной","падла",
    "падлы","падле","падлу","падлой","падлюка","падлючка","шалава","шалавы","шалаве",
    "шалаву","шалавой","шалавка","проститутка","проститутки","проститутке","проститутку",
    "проститут","проституция","шлюха","шлюхи","шлюхе","шлюху","шлюхой","шлюшка","шлюшки",
    "шлюшный","ублюдок","ублюдки","ублюдка","ублюдочный","ублюдский","выродок","выродки",
    "выродка","выродочный","дебил","дебилы","дебила","дебилка","дебильный","дебильно",
    "дебилизм","дебилоид","кретин","кретины","кретина","кретинка","кретинизм","кретинский",
    "идиот","идиоты","идиота","идиотка","идиотский","идиотизм","дурак","дураки","дурака",
    "дура","дурёха","дурацкий","придурок","придурки","придурка","придурочный","олух",
    "олухи","олуха","олушара","дегенерат","дегенераты","дегенератка","дегенеративный",
    "имбецил","имбецилы","имбецилка","имбецильный","скотоёб","скотоложство","зоофил",
    "зоофилы","зоофилия","педофил","педофилы","педофилка","педофилия","насильник",
    "насильники","насильница","насилие","убийца","убийцы","убийство","убивать","убил",
    "убила","мразота","мразина","мразёныш",
    # INGLIZCHA
    "fuck","fucking","fucked","fucker","fuckers","fucks","fuckface","motherfucker",
    "motherfucking","motherfuckers","motherfuck","shit","shits","shitty","shitting",
    "bullshit","shithead","shitheads","shitface","shithole","shitstorm","bitch","bitches",
    "bitchy","sonofabitch","bitching","bitched","asshole","assholes","ass","asses","arse",
    "arses","arsehole","arseholes","jackass","jackasses","dumbass","dumbasses","dick",
    "dicks","dickhead","dickheads","dickface","dickhole","pussy","pussies","pussys",
    "pussyhole","cunt","cunts","cunty","cuntface","bastard","bastards","bastardy",
    "bastardly","slut","sluts","slutty","sluttish","slutting","whore","whores","whoring",
    "whorish","whorehouse","idiot","idiots","idiotic","idiotically","stupid","stupids",
    "stupidity","stupidly","stupider","dumb","dumbs","dumbfuck","dumbfucks","moron",
    "morons","moronic","moronically","retard","retards","retarded","retardation","crap",
    "craps","crappy","crappier","damn","damns","damned","damning","goddamn","goddammit",
    "hell","hells","hellish","hellhole","piss","pissed","pissing","pisser","pissers",
    "pissface","cock","cocks","cocksucker","cocksuckers","cocksucking","nigger","niggers",
    "nigga","niggas","faggot","faggots","fag","fags","faggotry","faggoty","sex","sexual",
    "sexuality","sexy","sexiest","porn","porno","pornography","pornographic","pornos",
    "nude","nudes","naked","nakedness","orgy","orgies","orgasmic","orgasm","orgasms",
    "rape","rapes","raped","raping","rapist","rapists","pedophile","pedophiles","pedophilia",
    "pedophilic","kill","kills","killed","killing","killer","killers","murder","murders",
    "murdered","murdering","murderer","suicide","suicides","suicidal","terrorist",
    "terrorists","terrorism","drug","drugs","drugged","drugging","druggie","cocaine",
    "heroin","marijuana","weed","meth","ecstasy","bollocks","bugger","buggery","bloody",
    "wanker","wankers","twat","twats","twatty","tosser","tossers","toss","sod","sodding",
    "sodomite","sodomy","git","gits","prat","prats","pratty","numpty","numpties","bellend",
    "bellends","knob","knobs","knobhead","knobheads","knobend","prick","pricks","prickhead",
    "shag","shags","shagged","shagging","shagger","bollox","bollocking","bollock","nob",
    "nobs","nobhead","nobheads","minger","mingers","minging","scrub","scrubs","scrubby",
    "scumbag","scumbags","vermin","vermins","lowlife","lowlifes","creep","creeps","creepy",
    "creeper","freak","freaks","freaky","freakish","weirdo","weirdos","weirdy","psycho",
    "psychos","psychotic","psychopath","psychopaths","sociopath","sociopaths","sociopathic",
    "loser","losers","worthless","useless","pathetic","pitiful","ugly","uglier","ugliest",
    "fatty","fatties","fatso","fatass","skinny","skinnies","scrawny","gay","gays","gayness",
    "homo","homos","homosexual","lesbian","lesbians","lesbo","lesbos","dyke","dykes",
    "tranny","trannies","shemale","shemales","cripple","cripples","crippled","crip","midget",
    "midgets","dwarf","dwarfs","spastic","spastics","spaz","spazz","spazzes","mong","mongs",
    "mongoloid","mongoloids","chink","chinks","gook","gooks","kike","kikes","spic","spics",
    "wetback","wetbacks","beaner","beaners","towelhead","towelheads","raghead","ragheads",
    "cracker","crackers","honky","honkies","whitey","whities","redneck","rednecks","hillbilly",
    "hillbillies","yank","yanks","yankee","yankees","gypsy","gypsies","pikey","pikeys",
    "inbred","inbreds","inbreeding","blowjob","blowjobs","handjob","handjobs","footjob",
    "cum","cums","cumming","cumshot","cumslut","cumdumpster","jizz","jizzed","jizzing",
    "sperm","sperms","dildo","dildos","vibrator","vibrators","condom","condoms","hooker",
    "hookers","stripper","strippers","stripping","stripclub","brothel","brothels","pimp",
    "pimps","pimping","pimped","escort","escorts","escorting","camgirl","camgirls","camboy",
    "camboys","camsex","onlyfans","onlyfan",
    # TURKCHA
    "orospu","orospular","orospuçocuğu","sikerim","sikeyim","sikiyim","sikim","sikik",
    "sikiş","siktir","siktirgit","siktirip","siktirsin","amcık","amcıklar","amına","amını",
    "aminakoyim","amınakoyim","aminakoyayim","göt","götler","götü","götünü","götüne",
    "götveren","götverenler","yarrak","yarraklar","yarrağı","yarrağını","yarrakkafa","piç",
    "piçler","piçlik","piçkurusu","pezevenk","pezevenkler","pezevenklik","şerefsiz",
    "şerefsizler","şerefsizlik","hain","hainler","hainlik","alçak","alçaklar","alçaklık",
    "aptal","aptallar","aptallık","salak","salaklar","salaklık","gerizekalı","gerizekalılar",
    "gerizekalılık","budala","budalalar","budalalık","ahmak","ahmaklar","ahmaklık","beyinsiz",
    "beyinsizler","beyinsizlik","dangalak","dangalaklar","dangalaklık","şapşal","şapşallar",
    "şapşallık","hödük","hödükler","hödüklük","kaltak","kaltaklar","kaltaklık","sürtük",
    "sürtükler","sürtüklük","fahişe","fahişeler","fahişelik","kahpe","kahpeler","kahpelik",
    "gavat","gavatlar","gavatik","ibne","ibneler","ibnelik","top","toplar","topluk","puşt",
    "puştlar","puştluk","yavşak","yavşaklar","yavşaklık","döl","döller","dölkafa","meme",
    "memeler","memeli","taşak","taşaklar","taşşak","bok","boklar","boklu","boktan","sıç",
    "sıçmak","sıçtım","sıçtı","osur","osurmak","osuruk","osuruklar",
    # QOZOQCHA
    "қотақ","қотақтар","қотағы","қотағын","қотақбас","сік","сігу","сігеді","сіккіш","ам",
    "амдар","амды","амның","жезөкше","жезөкшелер","жезөкшелік","оңбаған","оңбағандар",
    "оңбағандық","сұмырай","сұмырайлар","сұмырайлық","арсыз","арсыздар","арсыздық",
    "ұятсыз","ұятсыздар","ұятсыздық","намыссыз","намыссыздар","намыссыздық","ақымақ",
    "ақымақтар","ақымақтық","ақылсыз","ақылсыздар","ақылсыздық","есалаң","есалаңдар",
    "есалаңдық","жынды","жындылар","жындылық","диуана","диуаналар","диуаналық","сараң",
    "сараңдар","сараңдық","қызғаншақ","қызғаншақтар","өтірікші","өтірікшілер","өтірікшілік",
    "ұры","ұрылар","ұрылық","қарақшы","қарақшылар","қарақшылық","қанішер","қанішерлер",
    "қанішерлік","зұлым","зұлымдар","зұлымдық","қатыгез","қатыгездер","қатыгездік",
    "мейірімсіз","мейірімсіздер","мейірімсіздік",
    # TOJIKCHA
    "коток","котокҳо","котока","котокаш","сик","сиккан","сиккунӣ","ам","амҳо","ами",
    "фоҳиша","фоҳишаҳо","фоҳишагӣ","бешарм","бешармҳо","бешармӣ","беҳаё","беҳаёҳо","беҳаёӣ",
    "номус","номуссӣ","аблаҳ","аблаҳҳо","аблаҳӣ","аҳмақ","аҳмақҳо","аҳмақӣ","девона",
    "девонаҳо","девонагӣ","ҷиннӣ","ҷинниҳо","ҷиннигӣ","дузд","дуздҳо","дуздӣ","роҳзан",
    "роҳзанҳо","роҳзанӣ","қотил","қотилҳо","қотилӣ","золим","золимҳо","золимӣ","бераҳм",
    "бераҳмҳо","бераҳмӣ",
    # ARABCHA
    "كس","كسمك","كسك","كسها","كسه","زب","زبك","زبي","زبكم","طيز","طياز","طيزك","طيزها",
    "شرموط","شراميط","شرموطة","شرموطات","قحبة","قحبات","قحاب","قحبتك","عرص","عرصات",
    "عرصة","عرصك","خول","خولات","خولة","خولك","منيوك","منيوكة","منيوكين","متناك","متناكة",
    "متناكين","ديوث","ديوثة","ديوثين","كلب","كلاب","كلبة","كلبتك","خنزير","خنازير",
    "خنزيرة","حمار","حمير","حمارة","حمارتك","غبي","أغبياء","غبية","غباء","أحمق","حمقى",
    "حمقاء","حمق","مجنون","مجانين","مجنونة","جنون","حقير","حقيرة","حقارة","أحقار","وضيع",
    "وضيعين","وضاعة","سافل","سافلين","سفالة","وقح","وقحين","وقاحة","لعنة","لعنات","ملعون",
    "ملعونة","زبالة","زبالات","زبال","زبالين","خرا","خراء","خرائي","خرائك","بول","بولة",
    "بولي","بولك","جنس","جنسي","جنسية","جنسيا","عاهرة","عاهرات","عاهرك","بورنو","بورن",
    "إباحي","إباحية","عاري","عارية","عاريين",
    # FORSCHA
    "کیر","کیرم","کیرت","کیرش","کس","کسم","کست","کسش","کص","کصم","کصت","کون","کونم","کونت",
    "کونش","جنده","جنده‌ها","جنده‌ات","جنده‌کش","فاحشه","فاحشه‌ها","فاحشه‌ات","حرومزاده",
    "حرومزاده‌ها","حروم","بی‌شرف","بی‌شرف‌ها","بی‌شرفی","بی‌ناموس","بی‌ناموس‌ها","بی‌ناموسی",
    "بی‌حیا","بی‌حیاها","بی‌حیایی","احمق","احمق‌ها","احمقی","احمقانه","خنگ","خنگ‌ها",
    "خنگی","خنگول","دیوانه","دیوانه‌ها","دیوانگی","مجنون","مجنون‌ها","مجنونی","کونی",
    "کونی‌ها","کون‌کش","پدرسگ","پدرسگ‌ها","مادرجنده","مادرجنده‌ها","خواهرجنده","خواهرجنده‌ها",
    "کیرخور","کیرخور‌ها","کیرخوری","کصکش","کصکش‌ها","کصکشی","گوه","گوه‌ها","گوه‌خور",
    "گوه‌خوری","شاش","شاشید","شاشیدن","شاشه","گوز","گوزید","گوزیدن","گوزو","لعنتی",
    "کثافت","کثافت‌ها","کثافتی","پست","پست‌ها","پستی","آشغال","آشغال‌ها","آشغالی","زباله",
    "زباله‌ها","سکس","سکسی","پورن","پورنو","پورنوگرافی","لخت","لختی","تجاوز","تجاوزگر",
    "قتل","قاتل","قاتلان","خودکشی","خودکش",
    # HINDCHA
    "चूतिया","चूतिये","चूतियों","गांड","गांडू","गांडुओं","भोसड़ी","भोसड़ीके","भोसड़ीवाले",
    "मादरचोद","मादरचोदों","मादरचोदी","बहनचोद","बहनचोदों","बहनचोदी","बेटीचोद","बेटीचोदों",
    "बेटीचोदी","लंड","लंडों","लंडे","लंडू","लौड़ा","लौड़े","लौड़ों","लौड़ी","चोद","चोदू",
    "चोदना","चोदाई","रंडी","रंडियों","रंडीबाज","रंडीबाजी","कुट्टी","कुट्टियों","छिनाल",
    "छिनालों","कमीना","कमीनों","नीच","नीचों","हरामी","हरामियों","हरामखोर","हरामखोरों",
    "साला","सालों","साली","कुत्ता","कुत्ते","कुत्तों","कुत्ती","सुअर","सुअरों","सुअरी",
    "गधा","गधों","गधी","पागल","पागलों","बेवकूफ","बेवकूफों","मूर्ख","मूर्खों","उल्लू",
    "जाहिल","जाहिलों","गंदा","गंदे","गंदों","गंदगी","बदबू","बदबूदार","मल","मलों","पेशाब",
    "पेशाबों","टट्टी","टट्टियों","गोबर","गोबरों","सेक्स","सेक्सी","पोर्न","पोर्नो",
    "पोर्नोग्राफी","नंगा","नंगे","नंगों","बलात्कार","बलात्कारी","हत्या","हत्यारा",
    "हत्यारों","आत्महत्या","आत्मघाती","आतंकवादी","आतंकवाद","नशा","नशे",
    # ISPANCHA
    "puta","putas","putita","putona","putero","puteros","mierda","mierdas","mierdero",
    "mierdoso","coño","coños","coñazo","coñito","joder","jodete","jódete","jodido",
    "jodida","jodidos","jodidas","joder","jodan","jodanse","polla","pollas","pollón",
    "polludo","pollera","pija","pijas","pijudo","verga","vergas","vergudo","vergüenza",
    "cabrón","cabrones","cabrona","cabronas","cabronada","pendejo","pendejos","pendeja",
    "pendejas","pendejada","pendejadas","culero","culeros","culera","culeras","culerada",
    "marica","maricas","maricón","maricones","maricona","mariconada","mariconear","joto",
    "jotos","jota","jotas","jotería","puñal","puñales","puñetero","puñetera","gilipollas",
    "gilipollez","gilipolleces","imbécil","imbéciles","imbecilidad","idiota","idiotas",
    "idiotez","idioteces","estúpido","estúpidos","estúpida","estúpidas","estupidez","tonto",
    "tontos","tonta","tontas","tontería","tonterías","animal","animales","animalada",
    "animaladas","bestia","bestias","bestialidad","bruto","brutos","bruta","brutas",
    "brutalidad","salvaje","salvajes","salvajada","salvajadas","asqueroso","asquerosos",
    "asquerosa","asquerosas","inmundo","inmundos","inmunda","inmundas","inmundicia",
    "porquería","porquerías","basura","basuras","escoria","escorias","lameculos","lamebotas",
    "chupapollas","chupavergas","mamón","mamones","mamona","mamonas","mamada","mamadas",
    "mamar","mamando","sexo","sexual","sexualidad","porno","pornografía","pornográfico",
    "desnudo","desnudos","desnuda","desnudas","desnudez","orgía","orgías","orgásmico",
    "orgasmo","orgasmos","violación","violaciones","violador","violadores","pedófilo",
    "pedófilos","pedofilia","matar","mata","maté","mató","mataron","matando","asesino",
    "asesinos","asesina","asesinas","asesinato","suicidio","suicidios","suicida","suicidas",
    "terrorista","terroristas","terrorismo","droga","drogas","drogado","drogados","drogadicto",
    "cocaína","heroína","marihuana","porro","porros",
    # FRANSUZCHA
    "putain","putains","pute","putes","merde","merdes","merdeux","merdeuse","con","cons",
    "connard","connards","connarde","connardes","conne","connes","connerie","conneries",
    "salaud","salauds","salope","salopes","enculé","enculés","enculée","enculées","enculer",
    "encule","baiser","baise","baisé","baisée","baisable","bite","bites","bitard","bitards",
    "couille","couilles","couillon","couillons","couillonner","chatte","chattes","chaton",
    "chatons","nique","niquer","niqué","niquée","foutre","foutu","foutue","foutus","foutues",
    "bordel","bordels","pd","pédé","pédés","pédale","pédales","pédéraste","tapette",
    "tapettes","tarlouze","tarlouzes","tantouze","tantouzes","tata","tatas","gouine",
    "gouines","goudou","goudous","nègre","nègres","négresse","négresses","négro","bicot",
    "bicots","bougnoule","bougnoules","raton","ratons","youpin","youpins","youpine",
    "youpines","feuj","feujs","crétin","crétins","crétine","crétines","crétinisme",
    "imbécile","imbéciles","imbécillité","idiot","idiots","idiote","idiotes","idiotie",
    "idioties","stupide","stupides","stupidité","stupidités","débile","débiles","débilité",
    "débilités","abruti","abrutis","abrutie","abruties","andouille","andouilles","cornichon",
    "cornichons","cornichonne","cornichonnes","cruche","cruches","nouille","nouilles",
    "banane","bananes","cloche","cloches","clochard","clochards","saleté","saletés","sale",
    "sales","salir","salissant","ordure","ordures","ordurier","ordurière","pourriture",
    "pourritures","pourri","pourris","pourrie","vermine","vermines","vermineux","charogne",
    "charognes","charognard","charognards","crapule","crapules","crapuleux","crapuleuse",
    "canaille","canailles","canaillerie","voyou","voyous","voyoute","voyoutes","bandit",
    "bandits","banditisme","criminel","criminels","criminelle","criminelles","meurtrier",
    "meurtriers","meurtrière","meurtrières","assassin","assassins","assassine","assassines",
    "tueur","tueurs","tueuse","tueuses","suicide","suicides","suicidaire","suicidaires",
    "terroriste","terroristes","terrorisme","drogue","drogues","drogué","drogués","droguée",
    "droguées","cocaïne","héroïne","marijuana","beuh","sexe","sexes","sexuel","sexuelle",
    "sexuellement","porno","pornographie","pornographique","nu","nus","nue","nues","nudité",
    "orgie","orgies","orgasmique","orgasme","orgasmes","viol","viols","violer","violé",
    "violée","violeur","violeurs","pédophile","pédophiles","pédophilie",
    # NEMISCHA
    "scheiße","scheisse","scheiß","scheiss","scheißkerl","scheißkerle","scheißen","fick",
    "ficken","fickt","gefickt","ficker","fickers","arsch","ärsche","arschloch","arschlocher",
    "arschgeige","arschgeigen","arschficker","hurensohn","hurensöhne","hure","huren",
    "hürchen","nutte","nutten","nuttig","schlampe","schlampen","schlampig","fotze","fotzen",
    "schwanz","schwänze","schwanzlutscher","pimmel","muschi","muschis","titten","titte",
    "wichser","wichse","wichsen","wichsvorlage","wixer","gewixxt","spast","spasten","spasti",
    "spastis","spastisch","missgeburt","missgeburten","idiot","idioten","idiotin",
    "idiotinnen","idiotisch","dummkopf","dummköpfe","dummheit","trottel","trottelin",
    "trottelhaft","depp","deppen","deppin","deppert","blödmann","blödmänner","vollidiot",
    "vollidioten","pisser","piss","pissen","gepisst","kacke","kacken","gekackt","kacker",
    "dreck","dreckig","dreckiger","mist","mists","mistig","kot","kots","kotig","abfall",
    "abfalls","abfällig","müll","mülls","müllig","sex","sexuell","sexuelle","sexualität",
    "porno","pornografie","pornografisch","nackt","nackte","nackter","nacktheit","orgie",
    "orgien","orgastisch","orgasmus","orgasmen","vergewaltigung","vergewaltigungen",
    "vergewaltiger","pädophil","pädophile","pädophilie","mord","morde","mörder","mörderin",
    "mörderisch","töten","tötet","getötet","tötung","selbstmord","selbstmorde","selbstmörder",
    "terrorist","terroristen","terrorismus","droge","drogen","drogenabhängig","drogensüchtig",
    "kokain","heroin","marihuana","kiffen",
    # ITALYANCHA
    "cazzo","cazzi","cazza","cazzone","cazzoni","cazzata","cazzate","cazzuto","cazzuta",
    "incazzato","incazzata","merda","merde","merdoso","merdosa","merdaccia","stronzo",
    "stronzi","stronza","stronze","stronzata","stronzate","stronzeggiare","figa","fighe",
    "fighetto","fighetta","figone","figona","fica","fiche","fichetto","fichetta","culo",
    "culi","culone","culona","culata","inculo","inculare","inculato","inculata","inculate",
    "puttana","puttane","puttanata","puttanate","puttaniere","troia","troie","troione",
    "troioni","troiata","troiate","mignotta","mignotte","zoccola","zoccole","bastardo",
    "bastardi","bastarda","bastarde","cornuto","cornuti","cornuta","cornute","coglione",
    "coglioni","cogliona","coglionata","coglionate","coglionare","minchia","minchie",
    "minchione","minchioni","minchiata","minchiate","minchioneria","pirla","pirle","pirlone",
    "pirloni","pirlata","pirlate","scemo","scemi","scema","sceme","scemenza","scemenze",
    "imbecille","imbecilli","imbecillità","idiota","idioti","idiotaggine","stupido","stupidi",
    "stupida","stupide","stupidaggine","cretino","cretini","cretina","cretine","cretinata",
    "deficiente","deficienti","deficienza","ritardato","ritardati","ritardata","ritardate",
    "handicappato","handicappati","sfigato","sfigati","sfigata","sfigate","sfiga","sfighe",
    "cesso","cessi","cessa","cesse","cessone","cessoni","schifo","schifi","schifoso",
    "schifosa","schifezza","schifezze","porcheria","porcherie","porco","porci","porca",
    "porche","porcata","porcate","porcile","porcili","sporco","sporchi","sporca","sporche",
    "sporcizia","sporcaccione","sporcaccioni","sporcacciona","lurido","luridi","lurida",
    "luride","luridezza","lercio","lerci","lercia","lercie","lerciume","immondo","immondi",
    "immonda","immonde","immondizia","feccia","fecce","feccioso","fecciosa","verme","vermi",
    "verminaio","verminai","verminoso","verminosa","sesso","sessi","sessuale","sessuali",
    "sessualità","porno","pornografia","pornografico","pornografica","nudo","nudi","nuda",
    "nude","nudità","orgia","orgie","orgasmico","orgasmo","orgasmi","stupro","stupri",
    "stupratore","stupratori","stuprare","pedofilo","pedofili","pedofilia","omicidio",
    "omicidi","omicida","assassino","assassini","assassina","assassine","assassinio",
    "suicidio","suicidi","suicida","terrorista","terroristi","terrorismo","droga","droghe",
    "drogato","drogati","drogata","drogate","cocaina","eroina","marijuana","erba","spinello",
    # PORTUGALCHA
    "porra","porras","porrada","porradas","merda","merdas","merdoso","merdosa","caralho",
    "caralhos","caralhudo","caralhada","foder","fodido","fodida","fodidos","fodidas","foda",
    "fodas","fodasse","fodão","fodona","puta","putas","putona","putaria","putarias","puto",
    "putos","putedo","cabrão","cabrões","cabronada","corno","cornos","corna","cornas",
    "cornudo","cornuda","viado","viados","viada","viadas","viadagem","bicha","bichas",
    "bichona","bichonas","bichice","boiola","boiolas","boiolagem","boiolice","paneleiro",
    "paneleiros","paneleira","paneleiras","pênis","peniano","peniana","pica","picas",
    "picada","picadas","pinto","pintos","pintinho","pintinhos","xoxota","xoxotas","xana",
    "xanas","xaninha","xaninhas","boceta","bocetas","buceta","bucetas","bucetão","peito",
    "peitos","peitão","peitões","peitinho","bunda","bundas","bundão","bundões","bundinha",
    "cu","cus","cuzinho","cuzinhos","cuzão","cuzões","ânus","anal","anais","idiota","idiotas",
    "idiotice","idiotices","imbecil","imbecis","imbecilidade","imbecilidades","estúpido",
    "estúpidos","estúpida","estúpidas","estupidez","burro","burros","burra","burras","burrice",
    "otário","otários","otária","otárias","otarice","babaca","babacas","babacada","trouxa",
    "trouxas","trouxice","trouxices","panaca","panacas","panacada","panacadas","palhaço",
    "palhaços","palhaça","palhaças","palhaçada","escroto","escrotos","escrota","escrotas",
    "escrotice","safado","safados","safada","safadas","safadeza","safadezas","safadice",
    "piranha","piranhas","piranhagem","piranhice","vagabunda","vagabundas","vagabundagem",
    "vagabundear","vadia","vadias","vadiagem","vadiar","galinha","galinhas","galinhagem",
    "galinhar","prostituta","prostitutas","prostituição","prostituir","meretriz","meretrizes",
    "meretrício","sexo","sexos","sexual","sexuais","sexualidade","pornô","pornografia",
    "pornográfico","pornográfica","nu","nus","nua","nuas","nudez","orgia","orgias",
    "orgástico","orgasmo","orgasmos","estupro","estupros","estuprador","estupradores",
    "estuprar","pedófilo","pedófilos","pedofilia","assassino","assassinos","assassina",
    "assassinas","assassinato","matar","mata","matei","matou","matando","matança",
    "suicídio","suicídios","suicida","suicidas","terrorista","terroristas","terrorismo",
    "droga","drogas","drogado","drogados","drogada","drogadas","cocaína","heroína",
    "maconha","marijuana","erva",
    # XITOYCHA
    "cao","caoni","caonima","cào","càonǐ","càonǐmā","bi","biao","biaozi","biǎozi",
    "bichi","bīchí","bī","bīliǎn","bīyǎng","diao","diǎo","diǎomáo","diǎonǐ","diǎonǐmā",
    "ji","jī","jībā","jība","lan","làn","lànbī","lànhè","ma","mā","māde","tāmāde",
    "shabi","shǎbī","sha","shǎ","shǎzi","shǎguā","hun","hùn","hùndàn","hùnzhàng",
    "wang","wáng","wángbādàn","wángbā","gou","gǒu","gǒuzázhǒng","gǒuniángyǎng","zhu",
    "zhū","zhūluó","zhūnǎo","chu","chù","chùsheng","jia","jiā","jiāhuo","xìngjiāo",
    "sèqíng","luǒ","luǒtǐ","quánluǒ","qiángjiān","qiángjiānfàn","shā","shārén",
    "shārénfàn","móushā","zìshā","kǒngbù","kǒngbùfènzǐ","kǒngbùzhǔyì",
    # YAPONCHA
    "kuso","kusō","kusottare","kusogaki","chikushō","chikusho","kisama","temee","temē",
    "teme","omae","omaera","shine","shinu","shinde","shindeiru","shineba","shineru",
    "baka","bakayarō","bakayarou","bakamono","aho","ahō","ahou","ahondara","manuke",
    "tonma","kusomiso","unko","unkō","unkou","unkosu","manko","omanko","chinpo","chinpō",
    "chinpou","chinko","chinkō","chinkou","paizuri","oppai","ketsu","ketsuana",
    "ketsumanko","bicchi","bitchi","sura","sekkusu","poruno","nūdo","zenra","reipu",
    "gōkan","goukan","korosu","koroshite","korose","jisatsu","jisatsusha","terorisuto",
    "terorizumu",
    # KOREYSCHA
    "ssibal","ssibaro","ssibalnom","jot","byeongsin","gaesaekki","gaejot","jiral","nom",
    "nyeon","sae","gogi","jjot","bori","bogo","sip","hal","meong","seks","ganggan",
    "salhae",
    # BOSHQA TILLAR
    "malakas","malaka","malakes","poutana","poutanes","poustis","pousti","gamoto",
    "gamimenos","skata","skatoula","vlaka","vlakes","vlakas","kreas","kreatos",
    "kurva","kurvák","kurvázik","bazmeg","bazdmeg","fasz","faszok","faszom","faszod",
    "picsa","picsák","picsába","geci","gecik","gecit","szar","szarok","hülye","hülyék",
    "hülyeség","pula","pule","pulii","pulă","muie","muist","muiere","fut","futut","fututa",
    "cacat","căcat","cacaturi","căcătură","cur","cururi","curva","curve","pizda","pizde",
    "pizdii","pizdă","bou","boi","boii","prost","proști","proastă","proaste","idioți",
    "idioată","idioate","kurove","kurvi","kurvata","pichka","pichki","pichkata","pichkite",
    "mamka","mamkata","mamkite","tatko","tatkoto","tatkite","kopele","kopelata","kopelina",
    "kopel","prosti","prosta","glupak","glupaci","glupachka","glupachki","jebem","jebemti",
    "jebote","jebo","kurac","kurca","kurcu","kurcem","sranje","sranja","sranjce","govno",
    "govna","govance","kurve","kurvi","kurvica","picka","picke","picki","pickica","seronja",
    "seronje","seronjica","budala","budale","budalica","budaletine","idioti","idiotkinja",
    "idiotizam","довбойоб","довбойоби","довбойоб",
    # REKLAMA SO'ZLARI (matnda ham ishlatiladi)
    "sotiladi","sotaman","sotmoqchiman","narxi","arzon","aksiya","chegirma","chegirmalar",
    "promokod","promo","sertifikat","sertifikatlar","cheat","cheats","cheating","hack",
    "hacks","hacking","lua","skript","script","uc sotiladi","uc sotaman","rp sotiladi",
    "karta sotiladi","akkaunt sotiladi","vip kanal","vipkanal","obuna bo'ling",
    "reklama qilaman","reklama qilamiz","sponsorlik qilaman",
]

# ============================================================
# TAQIQLANGAN EMOJILAR (STIKERLAR UCHUN)
# ============================================================
BAD_EMOJIS = [
    "🍆","🍑","🔞","💦","👅","🍌","❤️‍🔥","🥒","🌶️","💋","👙","🩲","🩱",
    "🔪","🩸","💉","🚬","💊","🔫","🗡️","⚔️","☠️","💀","👺","👹","😈",
    "🖕","🖐️","👆","🤬","🤮","🤢","🤧","🍺","🍻","🥃","🍷","🍾"
]

# ============================================================
# REKLAMA ANIQLASH UCHUN QO'SHIMCHA
# ============================================================
ADS_WORDS = [
    "cheat","cheats","cheating","hack","hacks","hacking","lua","skript","script",
    "sotiladi","sotaman","sotmoqchiman","narxi","arzon","aksiya","chegirma",
    "promokod","promo","sertifikat","kanal","kanalga","kanalimiz","obuna",
    "subscribe","reklama","sponsor","vip","premium","instagram","youtube",
    "tiktok","facebook","telegram","uc sotiladi","uc sotaman","rp sotiladi",
    "karta sotiladi","akkaunt sotiladi","akkauntlar","modmenu","mod menu",
]

# ============================================================
# COMMAND LISTS
# ============================================================
PRIVATE_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("cancel", "Cancel operation"),
    BotCommand("admin", "Bot statistics"),
    BotCommand("stats", "Bot statistics"),
    BotCommand("users", "Users list"),
    BotCommand("broadcast", "Broadcast message"),
    BotCommand("ban", "Ban user"),
    BotCommand("unban", "Unban user"),
    BotCommand("banned", "Banned users list"),
]

GROUP_ADMIN_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("setup", "Setup command menu"),
    BotCommand("mute", "Mute user (reply)"),
    BotCommand("unmute", "Unmute user (reply)"),
    BotCommand("ban", "Ban user (reply)"),
    BotCommand("unban", "Unban user (reply)"),
    BotCommand("clear", "Clear recent messages"),
    BotCommand("warns", "Check user warnings (reply)"),
    BotCommand("resetwarns", "Reset user warnings (reply)"),
]

GROUP_PUBLIC_COMMANDS = [BotCommand("start", "Start the bot")]

# ============================================================
# HTML
# ============================================================
INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>TOMMY BOT</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;padding:16px;background:#0a0820}
.container{max-width:500px;margin:0 auto}
.header{text-align:center;padding:55px 0 30px}
.header h1{color:#4CAF50;font-size:26px;font-weight:800}
.header p{color:#aaa;font-size:13px}
.card{background:rgba(255,255,255,0.06);border-radius:18px;padding:18px;margin-bottom:14px;border:1px solid rgba(255,255,255,0.08)}
.card-title{color:#4CAF50;font-size:15px;font-weight:700;margin-bottom:14px;text-transform:uppercase}
.info-row{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid rgba(255,255,255,0.06)}
.info-row:last-child{border-bottom:none}
.info-label{color:#999;font-size:13px}
.info-value{color:#fff;font-weight:600;font-size:13px}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>🎮 TOMMY BOT</h1><p>PUBG Mobile Panel</p></div>
  <div class="card"><div class="card-title">👤 Your Info</div>
    <div class="info-row"><span class="info-label">Name:</span><span class="info-value" id="user-name">...</span></div>
    <div class="info-row"><span class="info-label">ID:</span><span class="info-value" id="user-id">-</span></div>
  </div></div>
<script>
const tg=window.Telegram.WebApp;tg.expand();tg.ready();
const u=tg.initDataUnsafe.user;
if(u){document.getElementById('user-name').innerText=u.first_name||`User #${u.id}`;document.getElementById('user-id').innerText=u.id;}
</script></body></html>'''

# ============================================================
# SQLITE
# ============================================================
def init_db():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, player_id TEXT, classic_rank TEXT, ultimate_rank TEXT, kills TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, chat_id INTEGER, count INTEGER DEFAULT 0, last_warned TEXT, PRIMARY KEY (user_id, chat_id))""")
    conn.commit(); conn.close()

def save_user(uid, un, fn):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)",
        (uid, un or "", fn or "", datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def save_post(uid, pid, cr, ur, k):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT INTO posts (user_id,player_id,classic_rank,ultimate_rank,kills,created_at) VALUES (?,?,?,?,?,?)",
        (uid, pid, cr, ur, k, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def get_users_count():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); n = c.fetchone()[0]; conn.close(); return n

def get_posts_count():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts"); n = c.fetchone()[0]; conn.close(); return n

def get_today_users_count():
    today = datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d")
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (today + "%",))
    n = c.fetchone()[0]; conn.close(); return n

def get_all_users(limit=30):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, joined_at FROM users ORDER BY joined_at DESC LIMIT ?", (limit,))
    r = c.fetchall(); conn.close(); return r

def get_recent_posts(limit=10):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, player_id, classic_rank, ultimate_rank, kills, created_at FROM posts ORDER BY id DESC LIMIT ?", (limit,))
    r = c.fetchall(); conn.close(); return r

def ban_user(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO banned_users VALUES (?, ?)",
        (uid, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def unban_user(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE user_id = ?", (uid,))
    conn.commit(); conn.close()

def is_banned(uid):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (uid,))
    r = c.fetchone(); conn.close(); return r is not None

def get_banned_users():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT user_id, banned_at FROM banned_users ORDER BY banned_at DESC")
    r = c.fetchall(); conn.close(); return r

def add_warning(uid, chat_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT count FROM warnings WHERE user_id=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    if row:
        new_count = row[0] + 1
        c.execute("UPDATE warnings SET count=?, last_warned=? WHERE user_id=? AND chat_id=?",
            (new_count, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M"), uid, chat_id))
    else:
        new_count = 1
        c.execute("INSERT INTO warnings VALUES (?,?,?,?)", (uid, chat_id, new_count, datetime.now(TZ_TASHKENT).strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close(); return new_count

def get_warnings(uid, chat_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT count FROM warnings WHERE user_id=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone(); conn.close(); return row[0] if row else 0

def reset_warnings(uid, chat_id):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id=? AND chat_id=?", (uid, chat_id))
    conn.commit(); conn.close()

# ============================================================
# HELPERS
# ============================================================
def hide_id(pid):
    p = str(pid).strip()
    if len(p) <= 6: return p
    return p[:3] + "***" + p[-2:]

def is_valid_player_id(p):
    p = str(p).strip()
    if not p.isdigit() or len(p) != 11: return False
    if p[0] not in ("5", "6"): return False
    if len(set(p)) == 1: return False
    return True

def validate_pubg_screenshot(image_bytes):
    try:
        img = Image.open(BytesIO(image_bytes)); img.load()
    except Exception:
        return False, "Could not read image."
    w, h = img.size
    if w < 640 or h < 360: return False, "Resolution too low."
    if w <= h: return False, "Landscape only."
    return True, ""

def parse_duration(s):
    s = str(s).strip().lower()
    if not s: return None
    try:
        num = int(s[:-1]); unit = s[-1]
    except (ValueError, IndexError):
        try: num = int(s); unit = 'm'
        except ValueError: return None
    if num <= 0: return None
    if unit == 's': return timedelta(seconds=num)
    if unit == 'm': return timedelta(minutes=num)
    if unit == 'h': return timedelta(hours=num)
    if unit == 'd': return timedelta(days=num)
    if unit == 'w': return timedelta(weeks=num)
    return None

def human_duration(td):
    total = int(td.total_seconds())
    if total < 60: return f"{total} seconds"
    if total < 3600: return f"{total // 60} minutes"
    if total < 86400: return f"{total // 3600} hours"
    if total < 604800: return f"{total // 86400} days"
    return f"{total // 604800} weeks"

async def is_group_admin(update, context):
    chat = update.effective_chat; user = update.effective_user
    if chat.type not in ('group', 'supergroup'): return False
    try:
        member = await chat.get_member(user.id)
        return member.status in ('administrator', 'creator')
    except Exception: return False

async def check_group_admin(update, context):
    if not await is_group_admin(update, context):
        await update.message.reply_text("🚫 <b>Faqat guruh adminlari uchun.</b>", parse_mode='HTML')
        return False
    return True

# ============================================================
# GEMINI VISION — STIKER VA GIFNI TEKSHIRISH
# ============================================================
async def gemini_check_image(image_bytes: bytes) -> tuple:
    """
    Gemini AI orqali rasmni tekshiradi.
    Qaytaradi: (is_bad: bool, reason: str)
    """
    if not GEMINI_VISION_AVAILABLE:
        return False, ""
    try:
        img = Image.open(BytesIO(image_bytes))
        # Kichraytiramiz (tezroq ishlashi uchun)
        img.thumbnail((512, 512))
        buf = BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=70)
        img_bytes = buf.getvalue()
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Bu rasmni tahlil qil. Rasmda quyidagilar bormi: "
            "pornografiya, yalang'ochlik, jinsiy aloqa, jinsiy a'zolar, "
            "qon, zo'ravonlik, qurol, giyohvandlik, spirtli ichimlik, "
            "yoki bolalar uchun nomaqbul bo'lgan boshqa narsa? "
            "Faqat \"YES: sabab\" yoki \"NO\" deb javob ber."
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content([
            {"mime_type": "image/jpeg", "data": img_bytes},
            prompt
        ]))
        text = response.text.strip().upper()
        if text.startswith("YES"):
            return True, text.replace("YES:", "").strip()[:80]
        return False, ""
    except Exception as e:
        logger.error(f"Gemini vision error: {e}")
        return False, ""

# ============================================================
# COMMAND MENU SETUP
# ============================================================
async def setup_private_commands(application):
    try:
        await application.bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        logger.info("✅ Private commands set")
    except Exception as e:
        logger.error(f"❌ Private commands error: {e}")

async def setup_group_commands(application, chat_id):
    try:
        await application.bot.set_my_commands(GROUP_ADMIN_COMMANDS, scope=BotCommandScopeChatAdministrators(chat_id=chat_id))
        await application.bot.set_my_commands(GROUP_PUBLIC_COMMANDS, scope=BotCommandScopeChat(chat_id=chat_id))
        logger.info(f"✅ Group commands set for chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Group commands error for {chat_id}: {e}")

async def post_init(application):
    await setup_private_commands(application)

# ============================================================
# SEND TO TELEGRAM
# ============================================================
def send_to_telegram(image_bytes, caption, mime_type='image/jpeg'):
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('screenshot.jpg', image_bytes, mime_type)}
        data = {'chat_id': CHANNEL_ID, 'caption': caption}
        r = requests.post(url, files=files, data=data, timeout=60)
        return r.json()
    except Exception as e:
        return {'ok': False, 'description': str(e)}

# ============================================================
# FLASK
# ============================================================
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/*": {"origins": "*"}})

@flask_app.route('/', methods=['GET'])
def index():
    return Response(INDEX_HTML, mimetype='text/html')

@flask_app.route('/send-feedback', methods=['POST'])
def send_feedback():
    try:
        if 'photo' not in request.files:
            return jsonify({'ok': False, 'description': 'Photo required!'}), 400
        photo = request.files['photo']
        if photo.filename == '': return jsonify({'ok': False, 'description': 'No file'}), 400
        photo_bytes = photo.read()
        if len(photo_bytes) > 5*1024*1024: return jsonify({'ok': False, 'description': 'Too large'}), 400
        caption = request.form.get('caption', '')
        if not caption: return jsonify({'ok': False, 'description': 'Caption required!'}), 400
        tg_res = send_to_telegram(photo_bytes, caption, photo.mimetype or 'image/jpeg')
        return jsonify({'ok': tg_res.get('ok', False), 'description': tg_res.get('description')}), 200 if tg_res.get('ok') else 500
    except Exception as e:
        logger.error(f"❌ Web error: {e}")
        return jsonify({'ok': False, 'description': str(e)}), 500

def run_flask():
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)

# ============================================================
# USER COMMANDS
# ============================================================
async def start(update, context):
    u = update.effective_user
    if update.effective_chat.type == 'private' and is_banned(u.id):
        await update.message.reply_text("🚫 <b>Siz botdan bloklangansiz.</b>\n\nContact: @Tommy_1727", parse_mode='HTML')
        return
    save_user(u.id, u.username, u.first_name)
    context.user_data.clear()
    kb = [
        [InlineKeyboardButton("🏆 RANK STATISTICA", callback_data="rank_start")],
        [InlineKeyboardButton("📞 Contact", callback_data="contact")],
    ]
    await update.message.reply_text("🤖 TOMMY BOT\n\nPUBG Mobile statistikangizni yuboring:", reply_markup=InlineKeyboardMarkup(kb))

async def rank_start(update, context):
    q = update.callback_query; await q.answer(); context.user_data.clear()
    await q.message.reply_text("🆔 Step 1\n\nPUBG Mobile ID:\n\n• 11 ta raqam\n• 5 yoki 6 bilan boshlanadi\n\nMisol: 52254689580")
    return PLAYER_ID

async def handle_player_id(update, context):
    pid = update.message.text.strip()
    if not is_valid_player_id(pid):
        await update.message.reply_text("❌ Noto'g'ri ID!\n\nQayta yuboring:")
        return PLAYER_ID
    context.user_data['player_id'] = pid
    ranks = ["Bronze","Silver","Gold","Platinum","Diamond","Crown","Ace","Ace Master","Ace Dominator","Conqueror"]
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"classic_{r}")] for r in ranks]
    await update.message.reply_text(f"✅ ID: {pid}\n\n👑 Step 2\n\nCLASSIC RANK:", reply_markup=InlineKeyboardMarkup(kb))
    return CLASSIC

async def handle_classic(update, context):
    q = update.callback_query; await q.answer()
    rank = q.data.replace("classic_", ""); context.user_data['classic_rank'] = rank
    await q.message.delete()
    ranks = ["Vanguard","Exceed","Supreme","Peerless","Legend"]
    kb = [[InlineKeyboardButton(f"🏆 {r}", callback_data=f"ultimate_{r}")] for r in ranks]
    await q.message.reply_text(f"✅ Classic: {rank}\n\n👑 Step 3\n\nULTIMATE ROYALE RANK:", reply_markup=InlineKeyboardMarkup(kb))
    return ULTIMATE

async def handle_ultimate(update, context):
    q = update.callback_query; await q.answer()
    rank = q.data.replace("ultimate_", ""); context.user_data['ultimate_rank'] = rank
    await q.message.delete()
    await q.message.reply_text(f"✅ Ultimate: {rank}\n\n💀 Step 4\n\nKILLS (1-100):")
    return KILLS

async def handle_kills(update, context):
    kills = update.message.text.strip()
    if not kills.isdigit() or not (1 <= int(kills) <= 100):
        await update.message.reply_text("❌ 1-100 orasida raqam:")
        return KILLS
    context.user_data['kills'] = kills
    await update.message.reply_text(f"✅ Kills: {kills}\n\n📸 Step 5\n\nSkrinshot yuboring:")
    return PHOTO

async def handle_photo(update, context):
    photo = update.message.photo[-1]
    msg = await update.message.reply_text("⏳ Tekshirilmoqda...")
    try:
        f = await context.bot.get_file(photo.file_id)
        fb = bytes(await f.download_as_bytearray())
        ok, reason = validate_pubg_screenshot(fb)
        if not ok:
            await msg.delete()
            await update.message.reply_text(f"❌ {reason}\n\nQayta yuboring:")
            return PHOTO
        player_id = context.user_data.get('player_id', '')
        classic_rank = context.user_data.get('classic_rank', 'Unknown')
        ultimate_rank = context.user_data.get('ultimate_rank', 'Unknown')
        kills = context.user_data.get('kills', '0')
        hidden_id = hide_id(player_id)
        user = update.effective_user
        owner_d = f"@{user.username}" if user.username else user.full_name
        now = datetime.now(TZ_TASHKENT); time_str = now.strftime('%H:%M %d.%m.%Y')
        caption = (f"👤 OWNER: {owner_d}\n🎮 Player ID: {hidden_id}\n🏆 CLASSIC: {classic_rank}\n"
                   f"🏆 ULTIMATE: {ultimate_rank}\n🕒 TIME: {time_str}\n💀 KILL: {kills}\n\n👤 OWNER: {OWNER_FIXED} ✅")
        kb = [[InlineKeyboardButton("✅ Yuborish", callback_data="confirm_send")],
              [InlineKeyboardButton("❌ Bekor", callback_data="cancel_post")]]
        await msg.delete()
        context.user_data['photo_id'] = photo.file_id
        context.user_data['caption'] = caption
        await update.message.reply_photo(photo=photo.file_id, caption=f"🤖 Preview:\n\n{caption}", reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Photo: {e}")
        await update.message.reply_text(f"❌ {e}")
        return PHOTO

async def confirm_send(update, context):
    q = update.callback_query; await q.answer()
    photo_id = context.user_data.get('photo_id')
    caption = context.user_data.get('caption', '')
    if not photo_id:
        await q.message.reply_text("❌ Rasm topilmadi.")
        return
    try:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=caption)
        user = update.effective_user
        save_post(user.id, context.user_data.get('player_id',''), context.user_data.get('classic_rank',''),
                  context.user_data.get('ultimate_rank',''), context.user_data.get('kills',''))
        await q.message.delete()
        await q.message.reply_text("✅ Kanalga yuborildi!")
    except Exception as e:
        await q.message.reply_text(f"❌ {e}")
    context.user_data.clear()

async def cancel_post(update, context):
    q = update.callback_query; await q.answer(); context.user_data.clear()
    await q.message.delete(); await q.message.reply_text("❌ Bekor qilindi.")

async def contact(update, context):
    q = update.callback_query; await q.answer()
    await q.message.reply_text("Contact: @Tommy_1727")

async def cancel(update, context):
    context.user_data.clear(); context.user_data['broadcast_mode'] = False
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END

# ============================================================
# OWNER COMMANDS
# ============================================================
async def admin_stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    text = (f"📊 <b>STATISTIKA</b>\n\n👥 Users: <b>{get_users_count()}</b>\n"
            f"🆕 Bugun: <b>{get_today_users_count()}</b>\n📸 Postlar: <b>{get_posts_count()}</b>\n"
            f"🚫 Bloklangan: <b>{len(get_banned_users())}</b>\n")
    await update.message.reply_text(text, parse_mode='HTML')

async def users_list(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    users = get_all_users(limit=100)
    if not users:
        await update.message.reply_text("Foydalanuvchi yo'q."); return
    text = f"👥 <b>USERS ({len(users)})</b>\n\n"
    for i, (uid, un, fn, ja) in enumerate(users, 1):
        name = f"@{un}" if un else (fn if fn else "User")
        text += f"{i}. {name} — {ja}\n    ID: <code>{uid}</code>\n"
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await update.message.reply_text(chunk, parse_mode='HTML')

async def broadcast_cmd(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    context.user_data['broadcast_mode'] = True
    await update.message.reply_text("📢 Broadcast rejimi.\nXabar yuboring.\n/cancel — bekor qilish.", parse_mode='HTML')

async def handle_broadcast_message(update, context):
    if not context.user_data.get('broadcast_mode'): return
    if update.effective_user.id != ADMIN_ID: return
    t = update.message.text
    if not t: return
    context.user_data['broadcast_mode'] = False
    users = get_all_users(limit=1000); total = len(users); sent = 0; failed = 0
    p = await update.message.reply_text(f"📤 0/{total}")
    for idx, (uid, _, _, _) in enumerate(users, 1):
        try:
            await context.bot.send_message(chat_id=uid, text=t); sent += 1
        except Exception: failed += 1
        if idx % 10 == 0 or idx == total:
            try: await p.edit_text(f"📤 {idx}/{total}")
            except Exception: pass
    await p.edit_text(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}", parse_mode='HTML')

async def ban_cmd(update, context):
    chat = update.effective_chat; user = update.effective_user
    if chat.type == 'private':
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Siz admin emassiz!"); return
    else:
        if not await check_group_admin(update, context): return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            uid = int(context.args[0]); target = await context.bot.get_chat(uid)
        except Exception:
            await update.message.reply_text("❌ Noto'g'ri ID."); return
    else:
        await update.message.reply_text("Javob qilib /ban yozing yoki /ban ID.", parse_mode='HTML'); return
    if target.id == user.id:
        await update.message.reply_text("❌ O'zingizni bloklay olmaysiz."); return
    if chat.type in ('group','supergroup'):
        try:
            m = await chat.get_member(target.id)
            if m.status in ('administrator','creator'):
                await update.message.reply_text("❌ Adminni bloklab bo'lmaydi."); return
        except Exception: pass
    name = f"@{target.username}" if target.username else target.full_name
    try:
        if chat.type == 'private':
            ban_user(target.id)
            await update.message.reply_text(f"✅ {name} botdan bloklandi.", parse_mode='HTML')
        else:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=target.id)
            await update.message.reply_text(f"🔨 <b>{name}</b> guruhdan bloklandi.\n👮 {user.mention_html()}", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def unban_cmd(update, context):
    chat = update.effective_chat; user = update.effective_user
    if chat.type == 'private':
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Siz admin emassiz!"); return
    else:
        if not await check_group_admin(update, context): return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            uid = int(context.args[0]); target = await context.bot.get_chat(uid)
        except Exception:
            await update.message.reply_text("❌ Noto'g'ri ID."); return
    else:
        await update.message.reply_text("Javob qilib /unban yozing."); return
    name = f"@{target.username}" if target.username else target.full_name
    try:
        if chat.type == 'private':
            unban_user(target.id)
            await update.message.reply_text(f"✅ {name} blokdan chiqarildi.", parse_mode='HTML')
        else:
            await context.bot.unban_chat_member(chat_id=chat.id, user_id=target.id)
            await update.message.reply_text(f"🔊 <b>{name}</b> blokdan chiqarildi.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def banned_list_cmd(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    b = get_banned_users()
    if not b:
        await update.message.reply_text("✅ Bloklangan yo'q."); return
    text = f"🚫 <b>BANNED ({len(b)})</b>\n\n"
    for uid, when in b:
        text += f"• <code>{uid}</code> — {when}\n"
    await update.message.reply_text(text, parse_mode='HTML')

# ============================================================
# GROUP ADMIN COMMANDS
# ============================================================
async def setup_cmd(update, context):
    chat = update.effective_chat
    if chat.type not in ('group','supergroup'):
        await update.message.reply_text("❌ Faqat guruhlarda."); return
    if not await check_group_admin(update, context): return
    await setup_group_commands(context.application, chat.id)
    await update.message.reply_text("✅ Menyu o'rnatildi!", parse_mode='HTML')

async def mute_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat; user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /mute 1h yozing.", parse_mode='HTML'); return
    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("❌ O'zingizni mute qila olmaysiz."); return
    try:
        m = await chat.get_member(target.id)
        if m.status in ('administrator','creator'):
            await update.message.reply_text("❌ Adminni mute qilib bo'lmaydi."); return
    except Exception: pass
    duration = parse_duration(context.args[0]) if context.args else timedelta(hours=1)
    if not duration:
        await update.message.reply_text("❌ Noto'g'ri vaqt. Misol: 30s, 5m, 2h, 1d, 1w"); return
    if duration > timedelta(days=366): duration = timedelta(days=366)
    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now(timezone.utc) + duration)
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(f"🔇 <b>{name}</b> mute qilindi — <b>{human_duration(duration)}</b>.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def unmute_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat; user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /unmute yozing."); return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_audios=True,
                can_send_documents=True, can_send_photos=True, can_send_videos=True,
                can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True))
        name = f"@{target.username}" if target.username else target.full_name
        await update.message.reply_text(f"🔊 <b>{name}</b> mute dan chiqarildi.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", parse_mode='HTML')

async def clear_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    end_id = update.message.message_id
    start_id = update.message.reply_to_message.message_id if update.message.reply_to_message else max(1, end_id-50)
    status = await update.message.reply_text("🗑️ Tozalanmoqda...")
    d = 0; f = 0
    for mid in range(start_id, end_id+1):
        try: await context.bot.delete_message(chat_id=chat.id, message_id=mid); d += 1
        except Exception: f += 1
    try: await status.delete()
    except Exception: pass
    r = await context.bot.send_message(chat_id=chat.id, text=f"✅ O'chirildi: {d}\n❌ Xato: {f}", parse_mode='HTML')
    await asyncio.sleep(5)
    try: await r.delete()
    except Exception: pass

async def warns_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /warns yozing."); return
    target = update.message.reply_to_message.from_user
    count = get_warnings(target.id, chat.id)
    name = f"@{target.username}" if target.username else target.full_name
    await update.message.reply_text(f"⚠️ <b>{name}</b>: <b>{count}/5</b> ogohlantirish.", parse_mode='HTML')

async def resetwarns_cmd(update, context):
    if not await check_group_admin(update, context): return
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("Javob qilib /resetwarns yozing."); return
    target = update.message.reply_to_message.from_user
    reset_warnings(target.id, chat.id)
    name = f"@{target.username}" if target.username else target.full_name
    await update.message.reply_text(f"✅ <b>{name}</b> ogohlantirishlari tozalandi.", parse_mode='HTML')

# ============================================================
# AVTOMODERATSIYA
# ============================================================
async def process_violation(update, context, reason: str):
    chat = update.effective_chat; user = update.effective_user
    name = f"@{user.username}" if user.username else user.full_name
    try:
        if update.message: await update.message.delete()
    except Exception as e:
        logger.error(f"Delete error: {e}")
    count = add_warning(user.id, chat.id)
    if count >= 5:
        try:
            await context.bot.restrict_chat_member(chat_id=chat.id, user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now(timezone.utc) + timedelta(hours=1))
            reset_warnings(user.id, chat.id)
            w = await context.bot.send_message(chat_id=chat.id,
                text=f"🚫 <b>{name}</b> 5 marta qoidabuzarlik qildi. <b>1 soatga mute</b>!\nSabab: <b>{reason}</b>",
                parse_mode='HTML')
        except Exception as e:
            logger.error(f"Mute error: {e}"); return
    else:
        w = await context.bot.send_message(chat_id=chat.id,
            text=(f"⚠️ <b>{name}</b>\nSabab: <b>{reason}</b>\nOgohlantirish: <b>{count}/5</b>\n"
                  f"<i>5 tadan ko'p bo'lsa 1 soatga mute qilinasiz!</i>"), parse_mode='HTML')
    await asyncio.sleep(10)
    try: await w.delete()
    except Exception: pass

# ---------- MATN FILTRI ----------
async def text_filter(update, context):
    if not update.message or not update.message.text: return
    if await is_group_admin(update, context): return
    text = update.message.text
    low = text.lower()
    words = re.findall(r'\b\w+\b', low, flags=re.UNICODE)
    # 1. So'kinishlar
    found_bad = [w for w in words if w in BAD_WORDS]
    if not found_bad:
        for bw in BAD_WORDS:
            if len(bw) >= 5 and bw in low:
                found_bad.append(bw); break
    # 2. Havolalar
    links = re.findall(r'(https?://\S+|t\.me/\S+|www\.\S+)', low)
    # 3. @username
    usernames = re.findall(r'@[a-zA-Z0-9_]{4,}', text)
    # 4. Telefon
    phones = re.findall(r'(\+?\d[\d\s\-\(\)]{8,}\d)', text)
    # 5. Reklama so'zlari
    ads = [w for w in words if w in ADS_WORDS]
    # 6. Forward
    fwd = update.message.forward_from_chat is not None or update.message.forward_from is not None
    # 7. Emoji spam
    emoji_count = len(re.findall(r'[\U0001F300-\U0001FAFF\u2600-\u27BF]', text))
    
    reason = None
    if found_bad: reason = f"so'kinish ({', '.join(set(found_bad))[:30]})"
    elif links: reason = "havola"
    elif usernames: reason = "reklama (@username)"
    elif phones: reason = "telefon raqam"
    elif ads: reason = f"reklama ({', '.join(set(ads))[:30]})"
    elif fwd: reason = "kanaldan forward"
    elif emoji_count >= 6: reason = "emoji spam"
    if reason: await process_violation(update, context, reason)

# ---------- STIKER FILTRI ----------
async def sticker_filter(update, context):
    if not update.message or not update.message.sticker: return
    if await is_group_admin(update, context): return
    sticker = update.message.sticker
    emoji = sticker.emoji or ""
    # 1. Yomon emoji tekshirish
    if any(e in emoji for e in BAD_EMOJIS):
        await process_violation(update, context, f"taqiqlangan emoji {emoji}")
        return
    # 2. Gemini Vision orqali rasmni tekshirish
    if GEMINI_VISION_AVAILABLE:
        try:
            f = await context.bot.get_file(sticker.file_id)
            fb = bytes(await f.download_as_bytearray())
            is_bad, reason = await gemini_check_image(fb)
            if is_bad:
                await process_violation(update, context, f"yomon stiker ({reason})")
        except Exception as e:
            logger.error(f"Sticker gemini error: {e}")

# ---------- GIF / VIDEO / RASM / BOSHQA MEDIA ----------
async def media_filter(update, context):
    if not update.message: return
    if await is_group_admin(update, context): return
    reason = None
    file_id = None
    # Stiker alohida handlerda
    if update.message.animation:
        reason = "GIF/animatsiya"; file_id = update.message.animation.file_id
    elif update.message.video:
        reason = "video"; file_id = update.message.video.file_id
    elif update.message.video_note:
        reason = "video xabar"; file_id = update.message.video_note.file_id
    elif update.message.photo:
        reason = "rasm"; file_id = update.message.photo[-1].file_id
    elif update.message.voice:
        reason = "ovozli xabar"
    elif update.message.audio:
        reason = "audio fayl"
    elif update.message.document:
        reason = "dokument"
    elif update.message.location:
        reason = "joylashuv"
    elif update.message.contact:
        reason = "kontakt"

    if reason:
        # Gemini orqali vizual kontentni tekshirish (GIF, video, rasm uchun)
        if file_id and GEMINI_VISION_AVAILABLE and reason in ("GIF/animatsiya", "video", "video xabar", "rasm"):
            try:
                f = await context.bot.get_file(file_id)
                fb = bytes(await f.download_as_bytearray())
                is_bad, ai_reason = await gemini_check_image(fb)
                if is_bad:
                    await process_violation(update, context, f"{reason} ({ai_reason})")
                    return
                else:
                    # Yaxshi kontent — o'tkazib yuboramiz
                    return
            except Exception as e:
                logger.error(f"Media gemini error: {e}")
        # AI yo'q bo'lsa — barcha media o'chiriladi
        await process_violation(update, context, reason)

# ============================================================
# BOT ADDED TO GROUP
# ============================================================
async def on_bot_added_to_group(update, context):
    mcm = update.my_chat_member
    if not mcm: return
    chat = mcm.chat; ns = mcm.new_chat_member.status
    if chat.type in ('group','supergroup'):
        if ns in ('member','administrator'):
            await setup_group_commands(context.application, chat.id)
        elif ns in ('left','kicked'):
            try:
                await context.bot.delete_my_commands(scope=BotCommandScopeChatAdministrators(chat_id=chat.id))
                await context.bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=chat.id))
            except Exception: pass

# ============================================================
# START BOT
# ============================================================
def start_bot():
    logger.info("🤖 Bot starting...")
    try:
        req = HTTPXRequest(connection_pool_size=8, connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        application = (Application.builder().token(BOT_TOKEN).request(req).post_init(post_init).build())
        conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(rank_start, pattern="^rank_start$")],
            states={
                PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_player_id)],
                CLASSIC: [CallbackQueryHandler(handle_classic, pattern="^classic_")],
                ULTIMATE: [CallbackQueryHandler(handle_ultimate, pattern="^ultimate_")],
                KILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_kills)],
                PHOTO: [MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            per_message=False,
        )
        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv)
        application.add_handler(CallbackQueryHandler(confirm_send, pattern="^confirm_send$"))
        application.add_handler(CallbackQueryHandler(cancel_post, pattern="^cancel_post$"))
        application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
        # Owner
        application.add_handler(CommandHandler("admin", admin_stats))
        application.add_handler(CommandHandler("stats", admin_stats))
        application.add_handler(CommandHandler("users", users_list))
        application.add_handler(CommandHandler("broadcast", broadcast_cmd))
        application.add_handler(CommandHandler("ban", ban_cmd))
        application.add_handler(CommandHandler("unban", unban_cmd))
        application.add_handler(CommandHandler("banned", banned_list_cmd))
        # Group admin
        application.add_handler(CommandHandler("setup", setup_cmd))
        application.add_handler(CommandHandler("mute", mute_cmd))
        application.add_handler(CommandHandler("unmute", unmute_cmd))
        application.add_handler(CommandHandler("clear", clear_cmd))
        application.add_handler(CommandHandler("warns", warns_cmd))
        application.add_handler(CommandHandler("resetwarns", resetwarns_cmd))
        # Moderatsiya
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, text_filter))
        application.add_handler(MessageHandler(filters.Sticker & filters.ChatType.GROUPS, sticker_filter))
        application.add_handler(MessageHandler(
            (filters.ANIMATION | filters.VIDEO | filters.VIDEO_NOTE | filters.VOICE |
             filters.AUDIO | filters.Document | filters.PHOTO | filters.LOCATION | filters.CONTACT)
            & filters.ChatType.GROUPS, media_filter))
        # Broadcast
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.ChatType.PRIVATE,
            handle_broadcast_message))
        application.add_handler(ChatMemberHandler(on_bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))
        logger.info("✅ Bot started")
        application.run_polling(stop_signals=None, drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

def main():
    init_db()
    threading.Thread(target=start_bot, daemon=True).start()
    logger.info(f"🌐 Flask port: {PORT}")
    run_flask()

if __name__ == "__main__":
    main()
