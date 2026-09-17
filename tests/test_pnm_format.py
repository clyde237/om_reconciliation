"""Vérifie que la table de positions PNM décrit fidèlement les échantillons Sage réels.

Ces quatre fichiers sont la seule spécification disponible du format attendu par
l'installation Sage 100 du client (cahier des charges §11 : le format ne doit pas être
inventé). Si ce test casse, c'est la table `PNM_LAYOUT` qui est fausse, pas les fichiers.
"""

from pathlib import Path

import pytest

from config.sage_config import (
    PNM_CONSTANTS,
    PNM_ENCODING,
    PNM_HEADER_LENGTH,
    PNM_LAYOUT,
    PNM_LINE_ENDING,
    PNM_LINE_LENGTH,
)

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "templates" / "pnm_samples"


def read_sample(path: Path) -> tuple[str, list[str]]:
    """Retourne l'en-tête et les lignes d'écriture d'un fichier PNM."""
    raw = path.read_bytes().decode(PNM_ENCODING)
    lines = raw.split(PNM_LINE_ENDING)
    return lines[0], [line for line in lines[1:] if line]


def field(line: str, name: str) -> str:
    start, length, _ = PNM_LAYOUT[name]
    return line[start:start + length].strip()


def sample_files() -> list[Path]:
    return sorted(SAMPLES_DIR.glob("*.pnm"))


def test_les_echantillons_sont_presents():
    assert len(sample_files()) == 4


@pytest.mark.parametrize("path", sample_files(), ids=lambda p: p.stem)
def test_enveloppe_du_fichier(path: Path):
    raw = path.read_bytes()
    assert all(byte < 128 for byte in raw), "le format PNM est en ASCII strict"
    assert b"\n" not in raw.replace(b"\r\n", b""), "fins de ligne CRLF uniquement"

    header, entries = read_sample(path)
    assert len(header) == PNM_HEADER_LENGTH
    assert header.strip() == "Bijou SA"
    assert entries, "au moins une écriture"
    for line in entries:
        assert len(line) == PNM_LINE_LENGTH


@pytest.mark.parametrize("path", sample_files(), ids=lambda p: p.stem)
def test_champs_constants(path: Path):
    _, entries = read_sample(path)
    for line in entries:
        assert field(line, "journal") == "ACH"
        assert field(line, "date") == "110103"
        assert field(line, "sens") in {"D", "C"}
        assert field(line, "devise") == "EUR"
        for name, expected in PNM_CONSTANTS.items():
            assert field(line, name) == expected


@pytest.mark.parametrize("path", sample_files(), ids=lambda p: p.stem)
def test_montants_exploitables(path: Path):
    """Le champ montant se décode en nombre à deux décimales sur toutes les lignes."""
    from decimal import Decimal

    _, entries = read_sample(path)
    for line in entries:
        montant = field(line, "montant")
        assert Decimal(montant) > 0
        assert montant.split(".")[1] == montant.split(".")[1][:2]


def test_les_lignes_complementaires_partagent_le_numero_d_ecriture():
    """Une ligne mère et ses ventilations analytiques portent le même n° d'écriture."""
    header_path = SAMPLES_DIR / "ecritures multi axe analytique.pnm"
    _, entries = read_sample(header_path)

    meres = [l for l in entries if not field(l, "type_ligne")]
    analytiques = [l for l in entries if field(l, "type_ligne") == "A"]
    assert analytiques, "le fichier contient bien des ventilations analytiques"

    numeros_meres = {field(l, "numero_ecriture") for l in meres}
    for ligne in analytiques:
        assert field(ligne, "numero_ecriture") in numeros_meres
        assert field(ligne, "axe_analytique") in {"1", "2"}


def test_le_libelle_tient_sur_vingt_cinq_caracteres():
    """Borne relevée : docs/format_pnm.md §4 point 1 — à confronter à l'installation client."""
    for path in sample_files():
        _, entries = read_sample(path)
        for line in entries:
            start, length, _ = PNM_LAYOUT["libelle"]
            assert length == 25
            assert len(field(line, "libelle")) <= length
