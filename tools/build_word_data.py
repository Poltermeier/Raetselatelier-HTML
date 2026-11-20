"""Build the German word catalog from the pinned sources in third_party/NOTICE.md."""
import argparse
from html import unescape
import json
from pathlib import Path
import re
import unicodedata

GAME_WORD = re.compile(r"[a-zäöüß]{4,16}")
MORPHOLOGY_CLASSES = {"ADJ", "ADV", "PA1", "PA2", "SUB", "VER"}
WORDLE_SKIP = {
    "bumsen", "fotze", "latein", "pissen", "spass", "unter", "zuviel",
}

# Category words are editorially selected for recognizable spelling and clues.
THEMES = {
    "Tiere": (
        "adler affe ameise biber dachs delfin ente eule fisch fuchs giraffe hase hecht hund "
        "igel kakadu katze krabbe kröte lamm löwe luchs marder möwe otter pferd pinguin robbe "
        "schaf schwan siebenschläfer specht tiger wolf zebra ziege ameisenbär "
        "gartenschnecke klapperschlange schneeleopard schmetterling zauneidechse "
        "zwergfledermaus alpenschneehuhn albatros bärenmarder dromedar "
        "eichhörnchen eisvogel erdmännchen faultier flughund flussdelfin gürteltier hermelin "
        "känguru kolibri krokodil laubfrosch nachtigall nashorn natter papagei pelikan "
        "polarfuchs salamander schleiereule schnabeltier seelöwe "
        "silberfischchen vogelspinne wanderfalke waschbär wildschwein wüstenrennmaus "
    ),
    "Obst und Gemüse": (
        "ananas apfel avocado banane birne blumenkohl bohne brombeere brokkoli erbse erdbeere "
        "feige gurke himbeere kirsche kiwi kokosnuss lauch limette mango melone paprika "
        "pfirsich pflaume rettich rübe sellerie spargel spinat tomate zitrone zucchini "
        "zwiebel artischocke frühlingszwiebel granatapfel honigmelone johannisbeere "
        "stachelbeere zuckerschote wassermelone hokkaidokürbis aprikose bergpfirsich "
        "butterkürbis datteltomate feldsalat grapefruit heidelbeere kichererbse kohlrabi "
        "kopfsalat mandarine mangold nektarine pastinake preiselbeere "
        "rhabarber rosenkohl rotkohl schalotte steckrübe süßkartoffel weißkohl wirsing "
        "zuckermelone "
    ),
    "Musikinstrumente": (
        "akkordeon balalaika bassgeige becken cello flöte geige gitarre gong harfe horn "
        "klarinette klavier mandoline oboe orgel posaune saxofon trommel trompete tuba "
        "ukulele xylophon zither bassklarinette blockflöte dudelsack glockenspiel "
        "konzertflügel querflöte rhythmusgitarre schlagzeug tenorsaxofon waldzither "
        "altblockflöte bassflöte bratsche euphonium fagott glasharfe hackbrett "
        "kontrabass laute mundharmonika panflöte pauke schellenkranz "
        "traversflöte triangel tastenakkordeon waldhorn zugposaune "
    ),
    "Kleidung und Accessoires": (
        "anzug armband badehose bluse brille gürtel handschuh hemd hose jacke jeans kette "
        "kleid krawatte mantel mütze pullover ring rock sandale schal schleife schuh socke "
        "stiefel strumpf tasche weste badeanzug gürteltasche hausschuhe jogginghose "
        "lederjacke regenjacke schlafanzug schwimmbrille sonnenbrille turnschuhe wintermantel "
        "windjacke bomberjacke daunenjacke fingerhandschuh halskette kapuzenjacke "
        "kniestrumpf ledergürtel modeschmuck morgenmantel ohrring outdoorjacke "
        "regenmantel regenponcho rollkragenpulli schirmmütze schnürstiefel schneehose "
        "schwimmanzug sommerschuh strickjacke taschenuhr wanderstiefel winterstiefel "
    ),
    "Werkzeug und Werkstatt": (
        "bohrer feile hammer hobel kabel klammer kneifzange leiter meißel nägel pinsel "
        "raspel schere schraube säge spachtel spaten zange zollstock akkuschrauber "
        "bandschleifer bohrmaschine feuerlöscher gummihammer "
        "heißklebepistole holzbohrer kreissäge schleifpapier schraubendreher stichsäge "
        "wasserwaage werkzeugkasten abisolierzange bitaufsatz bolzenschneider "
        "drahtbürste gabelschlüssel handkreissäge heißluftgebläse kettensäge lackrolle "
        "lötstation maßband nagelzieher ringschlüssel rohrschneider rohrzange "
        "schleifklotz schraubstock schraubzwinge seitenschneider stechbeitel "
    ),
    "Verkehrsmittel": (
        "auto autobus ballon boot dampfer dreirad fahrrad fähre flugzeug gleiter gondel "
        "hubschrauber kajak kanu kutsche linienbus moped motorrad rikscha roller schiff "
        "segelboot straßenbahn taxi traktor doppeldecker draisine elektroroller güterzug "
        "krankenwagen lastkraftwagen lieferwagen rettungswagen verkehrsflugzeug wohnmobil "
        "zeppelin bergefahrzeug bimmelbahn campingbus dachseilbahn diesellokomotive "
        "elektrofahrrad feuerwehrwagen frachtflugzeug frachtschiff gleitschirm "
        "hangseilbahn kinderwagen küstenfrachter luftkissenboot müllwagen "
        "regionalbahn sattelzug seilbahn tauchboot tretboot umlaufseilbahn "
        "wasserflugzeug "
    ),
    "Wetter und Himmel": (
        "blitz donner frost gewitter hagel hitze kälte mond nebel orkan regen regenbogen "
        "schauer schnee schneefall sonne stern sturm unwetter wind wolke abenddämmerung "
        "gewitterwolke gewitterfront hagelschauer hochdruckgebiet luftfeuchtigkeit "
        "mondfinsternis morgenröte schneegestöber schneeregen sonnenaufgang sonnenfinsternis "
        "sturmwarnung tiefdruckgebiet wolkenbruch abendrot blitzschlag bodenfrost "
        "dämmerung graupelschauer herbststurm himmelsgewölbe "
        "hochnebel kondensstreifen luftdruck mondsichel polarlicht regentropfen "
        "schneeflocke schneeverwehung sommerhitze sternschnuppe sturmböe tauwetter "
        "wolkenlücke "
    ),
    "Am Körper": (
        "ader auge bauch daumen elle fersen finger gelenk hals hand haut herz hüfte kinn "
        "knie knochen kopf leber lippe lunge magen mund muskel nagel nase nieren rücken "
        "schulter sehne stirn wange zahn zehe zunge augenbraue bauchnabel fingerkuppe "
        "fingernagel handgelenk herzmuskel kehlkopf kniescheibe kreuzband lederhaut "
        "lendenwirbel nasenflügel schlüsselbein trommelfell wirbelsäule "
        "achillessehne armbeuge augenwinkel brustbein brustkorb ellenbogen "
        "gesichtsmuskel halswirbel hinterkopf "
        "kiefergelenk milchzahn mittelfinger oberarmmuskel ohrläppchen "
        "schneidezahn schulterblatt speicheldrüse stirnhöhle wadenbein wimpern "
    ),
    "Bäume und Blumen": (
        "ahorn akazie birke buche distel eiche efeu esche farn fichte flieder geranie "
        "hortensie iris kastanie klee krokus lärche lilie linde lotus magnolie mohn narzisse "
        "nelke palme pappel rose tanne tulpe veilchen weide zeder zyklame birkenfeige "
        "esskastanie feldahorn japanahorn kletterrose königskerze löwenzahn pfingstrose "
        "rosskastanie schneeglöckchen sonnenblume vergissmeinnicht waldveilchen winterlinde "
        "zwergkiefer apfelbaum azalee blutbuche edelkastanie elsbeere felsenkirsche "
        "frauenmantel goldlack hainbuche haselstrauch himalayazeder holunder "
        "korkeiche magnolienbaum maiglöckchen pfirsichbaum platane "
        "riesenmammutbaum salweide schmucklilie silberahorn steineiche "
        "sumpfdotterblume vogelbeere wollblume zierkirsche "
    ),
    "Küche und Tisch": (
        "besteck brett dose eimer flasche gabel glas kanne kelle kessel korb kuchen löffel "
        "messer mühle ofen pfanne reibe salz schale schüssel sieb tasse teller topf waage "
        "wasser dosenöffner eierbecher fleischwolf gewürzmühle gulaschtopf kaffeekanne "
        "kaffeemaschine knoblauchpresse küchenwaage pfannenwender salatschüssel schneidebrett "
        "suppenkelle wasserkocher zitronenpresse abtropfsieb auflaufform "
        "backblech brotmesser butterdose eieruhr fleischgabel fonduegabel "
        "gebäckzange geschirrtuch gewürzstreuer korkenzieher küchenmesser "
        "messbecher nudelholz pfannendeckel pizzaschneider servierplatte "
        "sparschäler spritzbeutel thermoskanne tischdecke "
    ),
    "Backwaren und Gebäck": (
        "apfelkuchen apfelstrudel bagel baguette baumkuchen berliner biskuit "
        "brezel butterkeks butterstreusel croissant donauwelle dinkelbrot "
        "fladenbrot franzbrötchen haferkeks hefezopf honigkuchen käsekuchen "
        "kirschstreusel knäckebrot laugenstange lebkuchen marmorkuchen mohnkuchen "
        "nussecke nusszopf pfannkuchen pumpernickel quarkbällchen roggenbrötchen "
        "rosinenbrot sandkuchen schokocroissant schokoladenkeks schwarzbrot "
        "spekulatius streuselkuchen vollkornbrot waffel windbeutel zimtschnecke "
        "zitronenkuchen zuckerschnecke"
    ),
    "Gewürze und Küchenkräuter": (
        "anis basilikum bärlauch bohnenkraut chilisalz curry currypulver dill "
        "estragon fenchelsamen galgant ingwer kardamom kerbel knoblauch koriander "
        "krauseminze kreuzkümmel kräutersalz kümmel kurkuma liebstöckel lorbeerblatt "
        "majoran meerrettich muskatnuss nelkenpfeffer oregano paprikapulver "
        "petersilie pfeffer pfefferminze piment rosmarin safran salbei "
        "schnittlauch schwarzkümmel selleriesalz senfkörner sternanis thymian "
        "wacholderbeeren zitronengras zitronenthymian zuckerzimt"
    ),
    "Getränke": (
        "apfelsaft apfelschorle ayran birnensaft buttermilch cappuccino chaisirup "
        "dinkelkaffee eistee erdbeermilch espresso früchtetee glühwein "
        "grüntee hafermilch haselnussmilch heißgetränk hibiskustee holundersaft "
        "ingwertee johannisbeersaft kakao karottensaft kirschsaft kokoswasser "
        "kräutertee lindenblütentee limonade malzkaffee mandelmilch mineralwasser "
        "orangensaft pfefferminztee radler reisdrink rotwein sauerkirschsaft "
        "schwarztee sekt smoothie sojamilch tafelwasser tomatensaft traubensaft "
        "vanillemilch weißbier zitronenlimonade"
    ),
    "Berufe": (
        "architekt astronom augenärztin augenoptiker bäcker bibliothekar biologin "
        "buchhändler buchhalter dachdecker dolmetscher elektriker erzieherin "
        "feuerwehrmann florist fotoreporter gärtner geigenbauer goldschmied "
        "hebamme imker informatiker journalistin kaminkehrer klempner konditor "
        "krankenpfleger lackierer lehrerin lokführer maurer mechaniker pilot "
        "postbotin raumausstatter sanitäter schauspieler schornsteinfeger "
        "seemann tierärztin tierpfleger tischler toningenieur trompetenbauer "
        "uhrmacher verkehrspolizist zahnarzt zimmermann"
    ),
    "Landschaften und Gewässer": (
        "auenwald bucht flachland flussaue flussdelta flussmündung flusstal "
        "gebirge gebirgsbach gletscher gletscherspalte hochebene hochgebirge "
        "hochland hochmoor insel inselgruppe kegelberg klamm küste küstenstreifen "
        "meeresbucht meeresgrund mittelgebirge moräne "
        "nebenfluss nordhang oase osthang plateau regenwald "
        "sandbank sandsteinfelsen schotterebene steilküste steppe "
        "strand sumpf talsohle tiefebene trockensteppe ufer unterlauf "
        "vulkankrater waldlichtung wasserfall wasserscheide wüste"
    ),
    "Gesteine und Mineralien": (
        "achat alabaster amethyst aquamarin basalt bergkristall bernstein bimsstein "
        "diamant dolomit edelstein feldspat feuerstein gelbgold gips gneis granat "
        "granit grauwacke hämatit kalksandstein kalkschiefer kalkstein karneol "
        "katzengold kieselstein lapislazuli lavagestein malachit marmor mondstein "
        "obsidian olivin onyx opal pyrit quarz quarzit rosenquarz rubin sandstein "
        "saphir schieferton schiefer smaragd speckstein tigerauge topas tonstein turmalin"
    ),
    "Weltraum und Astronomie": (
        "andromedagalaxie asteroid bahnneigung doppelstern erdachse erdbahn "
        "erdrotation erdschatten exoplanet fernrohr fixstern galaxie gasplanet "
        "halleykomet helixnebel himmelsäquator infrarotteleskop "
        "jupitermond komet kosmologie kugelsternhaufen lichtjahr magnitudenskala "
        "marsmond meteor meteorit milchstraße mondkrater mondoberfläche "
        "mondphase mondrakete mondscheibe morgendstern nebelwolke neptun "
        "neutronenstern orbit planet planetenbahn planetenmond quecksilber "
        "radioteleskop raumfähre raumkapsel raumsonde raumstation ringplanet "
        "satellit saturnring sonnenkorona sonnenfleck "
        "sonnensystem spiralgalaxie sternbild sternhaufen sternspektrum "
        "supernova teleskop umlaufbahn urknall vollmond zenit zwergplanet zwergstern"
    ),
    "Vögel": (
        "amsel austernfischer bachstelze baumfalke bergfink blässhuhn blaumeise "
        "braunkehlchen brautente buchfink buntspecht dohle dompfaff "
        "eichelhäher elster fasan feldlerche fischadler flamingo gänsesäger "
        "goldammer graureiher grünspecht habicht haubenmeise haubentaucher "
        "haussperling höckerschwan kanarienvogel kiebitz kleiber kohlmeise "
        "kranich kuckuck laubsänger mauersegler mäusebussard mönchsgrasmücke "
        "neuntöter nilgans rabenkrähe rauchschwalbe ringeltaube rotkehlchen "
        "rotschwanz schwarzspecht silberreiher storch stelzenläufer steinadler "
        "stieglitz stockente sumpfmeise turmfalke turteltaube waldkauz "
        "waldohreule wasseramsel weißstorch wellensittich "
        "zaunkönig zilpzalp zwergschnäpper"
    ),
    "Insekten": (
        "abendpfauenauge ameisenjungfer blattlaus "
        "bockkäfer borkenkäfer dickkopffalter "
        "eintagsfliege erdhummel färbermotte feldgrille feuerwanze fliege florfliege "
        "fruchtfliege gartenlaubkäfer gelbrandkäfer gleichflügler glühwürmchen "
        "grashüpfer haferlaus heuschrecke holzbiene holzwespe "
        "honigbiene hornisse hummel kaisermantel kartoffelkäfer kleidermotte "
        "kohlweißling kupferstecher laufkäfer libelle lilienhähnchen "
        "maikäfer marienkäfer maulwurfsgrille mehlkäfer "
        "ohrwurm rosenkäfer sandbiene schaben schlupfwespe schnake schwebfliege "
        "seidenspinner silberfisch stechmücke steinfliege steinhummel "
        "stubenhummel tagpfauenauge totengräber wasserläufer "
        "weidenbohrer wespe wiesenschnake zitronenfalter"
    ),
    "Sport und Bewegung": (
        "badminton bahnradsport basketball biathlon bodenturnen bouldern boxen "
        "brustschwimmen eishockey eiskunstlauf fechten federball fußball "
        "gerättauchen geräteturnen gewichtheben gymnastik halbmarathon handball "
        "hindernislauf hochsprung hürdenlauf inlinehockey judo kanurennsport "
        "karate kickboxen kugelstoßen langstreckenlauf leichtathletik marathon "
        "mehrkampf minigolf mountainbiken "
        "radball radrennen reckturnen reiten ringen rollkunstlauf rudern "
        "schach schießen schlittschuhlauf schwimmen segelfliegen segeln "
        "skilanglauf skispringen snowboarden speerwurf sportklettern sprint "
        "stabhochsprung surfen tennis tischtennis triathlon "
        "voltigieren volleyball wandern wasserball weitsprung zehntkampf"
    ),
    "Handarbeiten und Basteln": (
        "abpausen acrylfarbe aquarell bügelperlen buntpapier "
        "drahtschmuck falzbein farbkarton filznadel fingermalerei fädeln "
        "garnrolle gipsguss glasschneiden häkeln häkelnadel holzperlen "
        "kalligraphie karton klebestift kneten knopfloch knüpfen kreidestift "
        "kreuzstich laubsäge lederstempel malen kunsthandwerk mosaik "
        "nadelkissen nähmaschine nähnadel nähseide origami papierblume "
        "papierfalten modelliermasse quilten "
        "satinband scherenetui schnittmuster schnitzen siebdruck spinnrad "
        "stickgarn stickrahmen stopfen stricken strickliesel stricknadel "
        "tonpapier verzieren weben webrahmen zeichnen"
    ),
    "Im Garten": (
        "anzuchterde balkonpflanze bäumchen beetumrandung blumenkasten "
        "blumenkübel blumentopf blumenzwiebel erdbeerpflanze fruchtwechsel "
        "gartenbeet gartenhaus gartenschere gartenschlauch gartenteich "
        "gartenzaun gewächshaus gießkanne grabegabel gummistiefel harke "
        "hecke heckenschere hochbeet insektenhotel kompost kompostbehälter "
        "kräuterbeet kräuterspirale laubhaufen mulch pflanzkübel "
        "pflanzschaufel pflanztopf rankgitter rasen rasenkante rasenmäher "
        "rasensprenger regentonne rechen rosenbogen saatgut "
        "samentütchen schubkarre steingarten tomatenpflanze trittstein "
        "vogelbad vogelscheuche wurmkiste"
    ),
    "Schule und Unterricht": (
        "arbeitsblatt aufgabenheft aufsatz bleistift buntstift federmappe "
        "ferien füller geodreieck geometrie grundschule hausaufgabe "
        "heftumschlag klassenarbeit klassenausflug "
        "klassenraum klassensprecher kreide kunstunterricht lehrbuch "
        "lernkarte lernstoff lineal locher löschpapier mathematik "
        "mitschüler nachmittagskurs notenheft pausenaufsicht pausenhof "
        "radiergummi rechenaufgabe referat schülerzeitung schulbuch "
        "schulgebäude schulklingel schulpult schulranzen schultafel "
        "schultasche schwammtuch spitzer sporthalle stundenplan tafel "
        "tafelkreide taschenrechner textmarker unterricht vokabelheft zeugnis zirkel"
    ),
    "Technik im Alltag": (
        "adapter antenne armatur bandlaufwerk batteriefach bildschirm "
        "bildtrommel blitzlicht datenleitung digitalkamera drucker "
        "zahnbürste fernbedienung festnetztelefon "
        "festplatte flachbildschirm funksteckdose hörgerät "
        "kabeltrommel kaffeemühle kalkfilter kopfhörer ladegerät "
        "ladekabel lautsprecher leselampe lichtschalter messgerät mikrofon "
        "mikrowelle netzkabel netzteil nachtsichtgerät rasierapparat "
        "rauchmelder schlüsselfinder schnurlostelefon sicherungskasten "
        "smartphone staubsauger steckdose stromanschluss tablet tastatur "
        "taschenlampe telefonkabel temperaturfühler thermostat tonabnehmer "
        "türklingel ventilator videokamera wäschetrockner zeitschaltuhr"
    ),
}


def normalize(text):
    return unicodedata.normalize("NFC", text.strip()).lower()


def read_frequency(path):
    counts = {}
    with path.open(encoding="utf-8") as source:
        for line in source:
            word, count = line.rsplit(maxsplit=1)
            word = normalize(word)
            count = int(count)
            if count >= 8 and GAME_WORD.fullmatch(word):
                counts[word] = max(count, counts.get(word, 0))
    return counts


def morphology_words(path, frequencies):
    words = set()
    targets = set()
    names = set()
    with path.open(encoding="utf-8") as source:
        for line in source:
            lemma, form, tags = line.split("_", 2)
            word = normalize(form)
            count = frequencies.get(word, 0)
            if count < 15:
                continue
            word_class, _, features = tags.strip().partition(":")
            if word_class in MORPHOLOGY_CLASSES:
                words.add(word)
            if len(word) not in (5, 6) or count < 400 or word != normalize(lemma):
                continue
            if word_class == "EIG":
                names.add(word)
            elif (word_class == "SUB" and features.startswith("NOM:") and not features.endswith((":ADJ", ":INF"))
                  or word_class == "VER" and features.startswith("INF:")
                  or word_class == "ADJ" and features == "PRD:GRU"):
                targets.add(word)
    return words, targets - names - WORDLE_SKIP


def build(odenet, frequency, morphology):
    # Extract the lemma tags directly. The source contains malformed Sense tags.
    lemmas = {normalize(unescape(word)) for word in re.findall(
        r'<Lemma\s+writtenForm="([^"]+)"\s+partOfSpeech="[nvars]"', odenet.read_text(encoding="utf-8"))}
    counts = read_frequency(frequency)
    forms, base_forms = morphology_words(morphology, counts)
    themes = {theme: sorted({word for word in words.split() if GAME_WORD.fullmatch(word)})
              for theme, words in THEMES.items()}
    editorial = {word for words in themes.values() for word in words}
    words = (lemmas & counts.keys()) | editorial | forms
    targets = (base_forms & lemmas) | {word for word in editorial if len(word) in (5, 6)}
    bee_common = sorted(word for word in forms if 4 <= len(word) <= 9
                        and len(set(word)) == len(word) and counts[word] >= 300)
    return {"words": sorted(words), "wordle": sorted(targets), "bee_common": bee_common, "themes": themes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odenet", type=Path)
    parser.add_argument("frequency", type=Path)
    parser.add_argument("morphology", type=Path)
    args = parser.parse_args()
    destination = Path(__file__).resolve().parents[1] / "raetselkalender/data/german_words.json"
    destination.write_text(json.dumps(build(args.odenet, args.frequency, args.morphology), ensure_ascii=False,
                                      separators=(",", ":")) + "\n", encoding="utf-8")
