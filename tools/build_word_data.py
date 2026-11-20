"""Build the German word catalog from the two pinned sources in third_party/NOTICE.md."""
import argparse
from html import unescape
import json
from pathlib import Path
import re
import unicodedata

# Category words are editorially selected for recognizable spelling and clues.
THEMES = {
    "Tiere": (
        "adler affe ameise biber dachs delfin ente eule fisch fuchs giraffe hase hecht hund "
        "igel kakadu katze krabbe kröte lamm löwe luchs marder möwe otter pferd pinguin robbe "
        "schaf schwan siebenschläfer specht tiger uhu wal wolf zebra ziege ameisenbär "
        "gartenschnecke klapperschlange schneeleopard schmetterling zauneidechse "
        "wasserschildkröte zwergfledermaus alpenschneehuhn "
    ),
    "Obst und Gemüse": (
        "ananas apfel avocado banane birne blumenkohl bohne brombeere brokkoli erbse erdbeere "
        "feige gurke himbeere kirsche kiwi kokosnuss lauch limette mango melone paprika "
        "pfirsich pflaume rettich rübe sellerie spargel spinat tomate zitrone zucchini "
        "zwiebel artischocke frühlingszwiebel granatapfel honigmelone johannisbeere "
        "stachelbeere zuckerschote wassermelone hokkaidokürbis "
    ),
    "Musikinstrumente": (
        "akkordeon balalaika bassgeige becken cello flöte geige gitarre gong harfe horn "
        "klarinette klavier mandoline oboe orgel posaune saxofon trommel trompete tuba "
        "ukulele xylophon zither bassklarinette blockflöte dudelsack glockenspiel "
        "konzertflügel querflöte rhythmusgitarre schlagzeug tenorsaxofon waldzither "
    ),
    "Kleidung und Accessoires": (
        "anzug armband badehose bluse brille gürtel handschuh hemd hose hut jacke jeans kette "
        "kleid krawatte mantel mütze pullover ring rock sandale schal schleife schuh socke "
        "stiefel strumpf tasche weste badeanzug gürteltasche hausschuhe jogginghose "
        "lederjacke regenjacke schlafanzug schwimmbrille sonnenbrille turnschuhe wintermantel "
        "windjacke "
    ),
    "Werkzeug und Werkstatt": (
        "bohrer feile hammer hobel kabel klammer kneifzange leiter lot meißel nägel pinsel "
        "raspel schere schraube säge spachtel spaten zange zollstock akkuschrauber "
        "bandschleifer bohrmaschine drehmomentschlüssel feuerlöscher gummihammer "
        "heißklebepistole holzbohrer kreissäge schleifpapier schraubendreher stichsäge "
        "wasserwaage werkzeugkasten "
    ),
    "Verkehrsmittel": (
        "auto autobus ballon boot dampfer dreirad fahrrad fähre flugzeug gleiter gondel "
        "hubschrauber kajak kanu kutsche linienbus moped motorrad rikscha roller schiff "
        "segelboot straßenbahn taxi traktor zug doppeldecker draisine elektroroller güterzug "
        "krankenwagen lastkraftwagen lieferwagen rettungswagen verkehrsflugzeug wohnmobil "
        "zeppelin "
    ),
    "Wetter und Himmel": (
        "blitz donner eis frost gewitter hagel hitze kälte mond nebel orkan regen regenbogen "
        "schauer schnee schneefall sonne stern sturm tau unwetter wind wolke abenddämmerung "
        "gewitterwolke gewitterfront hagelschauer hochdruckgebiet luftfeuchtigkeit "
        "mondfinsternis morgenröte schneegestöber schneeregen sonnenaufgang sonnenfinsternis "
        "sturmwarnung tiefdruckgebiet wolkenbruch "
    ),
    "Am Körper": (
        "ader auge bauch daumen elle fersen finger fuß gelenk hals hand haut herz hüfte kinn "
        "knie knochen kopf leber lippe lunge magen mund muskel nagel nase nieren rücken "
        "schulter sehne stirn wange zahn zehe zunge augenbraue bauchnabel fingerkuppe "
        "fingernagel handgelenk herzmuskel kehlkopf kniescheibe kreuzband lederhaut "
        "lendenwirbel nasenflügel schlüsselbein trommelfell wirbelsäule "
    ),
    "Bäume und Blumen": (
        "ahorn akazie birke buche distel eiche efeu esche farn fichte flieder geranie "
        "hortensie iris kastanie klee krokus lärche lilie linde lotus magnolie mohn narzisse "
        "nelke palme pappel rose tanne tulpe veilchen weide zeder zyklame birkenfeige "
        "esskastanie feldahorn japanahorn kletterrose königskerze löwenzahn pfingstrose "
        "rosskastanie schneeglöckchen sonnenblume vergissmeinnicht waldveilchen winterlinde "
        "zwergkiefer "
    ),
    "Küche und Tisch": (
        "besteck brett dose eimer flasche gabel glas kanne kelle kessel korb kuchen löffel "
        "messer mühle ofen pfanne reibe salz schale schüssel sieb tasse teller topf waage "
        "wasser dosenöffner eierbecher fleischwolf gewürzmühle gulaschtopf kaffeekanne "
        "kaffeemaschine knoblauchpresse küchenwaage pfannenwender salatschüssel schneidebrett "
        "suppenkelle wasserkocher zitronenpresse "
    ),
}


def normalize(text):
    return unicodedata.normalize("NFC", text.strip()).lower()


def build(odenet, frequency):
    # Extract the lemma tags directly. The source contains malformed Sense tags.
    lemmas = {normalize(unescape(word)) for word in re.findall(
        r'<Lemma\s+writtenForm="([^"]+)"\s+partOfSpeech="[nvars]"', odenet.read_text(encoding="utf-8"))}
    common = set()
    for line in frequency.read_text(encoding="utf-8").splitlines():
        word, count = line.rsplit(maxsplit=1)
        if int(count) >= 8:
            common.add(normalize(word))
    themes = {theme: sorted({normalize(word) for word in words.split() if 4 <= len(word) <= 16})
              for theme, words in THEMES.items()}
    editorial = {word for words in themes.values() for word in words}
    words = sorted(word for word in (lemmas & common) | editorial if re.fullmatch(r"[a-zäöüß]{4,16}", word))
    return {"words": words, "themes": themes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odenet", type=Path)
    parser.add_argument("frequency", type=Path)
    args = parser.parse_args()
    destination = Path(__file__).resolve().parents[1] / "raetselkalender/data/german_words.json"
    destination.write_text(json.dumps(build(args.odenet, args.frequency), ensure_ascii=False,
                                      separators=(",", ":")) + "\n", encoding="utf-8")
