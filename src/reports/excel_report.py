"""Générateur de rapport Excel d'audit multi-onglets (OpenPyXL).

Produit le classeur complet à 7 feuilles conforme au §9 du cahier des charges :
1. Synthèse (KPIs, 11 contrôles §8, ventilation par compte OM / point de vente)
2. Rapprochement (Tableau complet ligne par ligne)
3. Anomalies (Transactions nécessitant un contrôle ou bloquantes)
4. Manquants_Journal (Transactions OM sans arrhes comptables)
5. Manquants_OM (Arrhes comptables sans encaissement OM)
6. Doublons (Doublons potentiels détectés des deux côtés)
7. Contrôle_Mensuel (Suivi journalier / mensuel des flux)
"""

import io
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Sequence, Union

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config.matching_config import BLOCKING_STATUSES, MatchStatus
from src.analysis.anomalies import extraire_anomalies
from src.analysis.duplicates import extraire_doublons
from src.analysis.missing import extraire_manquants_journal, extraire_manquants_om
from src.analysis.monthly_summary import (
    SyntheseMensuelle,
    generer_synthese_mensuelle,
    ventiler_par_compte,
)
from src.analysis.reconciliation import (
    ControlesGlobaux,
    LigneRapprochement,
    calculer_controles,
    construire_table,
)
from src.matching.appariement import ResultatRapprochement
from src.normalization.amounts import ZERO
from src.reports.formatting import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    BORDER_THIN,
    BORDER_TOP_BOTTOM_DOUBLE,
    FILL_HEADER,
    FILL_SUBHEADER,
    FILL_TOTAL,
    FILL_ZEBRA_EVEN,
    FILL_ZEBRA_ODD,
    FONT_DATA,
    FONT_DATA_BOLD,
    FONT_HEADER,
    FONT_MUTED,
    FONT_SECTION,
    FONT_TITLE,
    FORMAT_DATE,
    FORMAT_MONTANT_FCFA,
    FORMAT_NOMBRE_ENTIER,
    FORMAT_POURCENTAGE,
    NAVY_HEADER,
    ORANGE_OM,
    ajuster_largeurs_colonnes,
    appliquer_style_donnees,
    appliquer_style_entete,
    appliquer_style_statut,
)


class ExcelReportGenerator:
    """Construit et exporte le classeur d'audit Excel à 7 feuilles."""

    def __init__(self, output_dir: Union[str, Path] = "data/output"):
        self.output_dir = Path(output_dir)

    def generate(
        self,
        source: Union[ResultatRapprochement, Sequence[ResultatRapprochement], SyntheseMensuelle],
        filename: str = "",
    ) -> Path:
        """Génère le classeur Excel sur disque et retourne son chemin."""
        wb = self._build_workbook(source)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            periode_str = self._extraire_nom_periode(source)
            filename = f"Rapprochement_OM_{periode_str}.xlsx"

        filepath = self.output_dir / filename
        wb.save(filepath)
        return filepath

    def generate_bytes(
        self,
        source: Union[ResultatRapprochement, Sequence[ResultatRapprochement], SyntheseMensuelle],
    ) -> io.BytesIO:
        """Génère le classeur Excel en mémoire sous forme de flux binaire BytesIO."""
        wb = self._build_workbook(source)
        tampon = io.BytesIO()
        wb.save(tampon)
        tampon.seek(0)
        return tampon

    def _extraire_nom_periode(self, source) -> str:
        if isinstance(source, SyntheseMensuelle):
            return source.periode_libelle.replace(" ", "_").replace("/", "-")
        if isinstance(source, ResultatRapprochement):
            return source.periode.libelle.replace(" ", "_").replace("/", "-")
        if isinstance(source, Sequence) and source:
            return source[0].periode.libelle.replace(" ", "_").replace("/", "-")
        return "Audit"

    def _build_workbook(
        self,
        source: Union[ResultatRapprochement, Sequence[ResultatRapprochement], SyntheseMensuelle],
    ) -> openpyxl.Workbook:
        """Assemble les 7 feuilles du rapport d'audit."""
        if isinstance(source, SyntheseMensuelle):
            synthese = source
            resultat_principal = None
            resultats_liste = []
        elif isinstance(source, ResultatRapprochement):
            synthese = generer_synthese_mensuelle(source)
            resultat_principal = source
            resultats_liste = [source]
        else:
            resultats_liste = list(source)
            if not resultats_liste:
                raise ValueError("Source vide : impossible de générer le rapport Excel.")
            synthese = generer_synthese_mensuelle(resultats_liste)
            resultat_principal = resultats_liste[0]

        wb = openpyxl.Workbook()
        # Supprimer la feuille par défaut
        wb.remove(wb.active)

        # 1. Synthèse
        self._creer_feuille_synthese(wb, synthese)

        # Extraction des tables consolidées
        tables_lignes: list[LigneRapprochement] = []
        for r in resultats_liste:
            tables_lignes.extend(construire_table(r))

        # 2. Rapprochement
        self._creer_feuille_rapprochement(wb, tables_lignes)

        # 3. Anomalies
        self._creer_feuille_anomalies(wb, tables_lignes)

        # 4. Manquants_Journal
        self._creer_feuille_manquants_journal(wb, tables_lignes, resultats_liste)

        # 5. Manquants_OM
        self._creer_feuille_manquants_om(wb, tables_lignes)

        # 6. Doublons
        self._creer_feuille_doublons(wb, resultats_liste)

        # 7. Contrôle_Mensuel
        self._creer_feuille_controle_mensuel(wb, synthese)

        return wb

    # --------------------------------------------------------------------------
    # 1. Feuille Synthèse
    # --------------------------------------------------------------------------
    def _creer_feuille_synthese(self, wb: openpyxl.Workbook, synthese: SyntheseMensuelle):
        ws = wb.create_sheet(title="Synthèse")
        ws.views.sheetView[0].showGridLines = True

        # Titre
        ws.cell(row=1, column=1, value="RAPPORT D'AUDIT & RAPPROCHEMENT ORANGE MONEY").font = FONT_TITLE
        ws.cell(row=2, column=1, value=f"Période auditée : {synthese.periode_libelle}").font = FONT_SECTION
        ws.cell(
            row=3,
            column=1,
            value=f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — Système OM Reconciliation",
        ).font = FONT_MUTED

        # Statut global badge
        controles = synthese.controles_globaux
        statut_txt = "CONFORME — AUCUNE ANOMALIE BLOQUANTE" if controles.nb_anomalies == 0 else f"EXPORT BLOQUÉ — {controles.nb_anomalies} ANOMALIE(S) À RÉSOUDRE"
        bg_statut = "DCFCE7" if controles.nb_anomalies == 0 else "FEE2E2"
        fg_statut = "166534" if controles.nb_anomalies == 0 else "991B1B"

        cell_badge = ws.cell(row=5, column=1, value=f"Statut Global : {statut_txt}")
        cell_badge.font = Font(name="Calibri", size=11, bold=True, color=fg_statut)
        cell_badge.fill = PatternFill(start_color=bg_statut, end_color=bg_statut, fill_type="solid")
        cell_badge.border = BORDER_THIN
        cell_badge.alignment = ALIGN_LEFT
        ws.merge_cells("A5:D5")

        # Section 1 : Indicateurs de Contrôle Global (§8)
        ws.cell(row=7, column=1, value="1. Contrôles Globaux de Réconciliation (§8)").font = FONT_SECTION

        headers_ctrl = ["Indicateur", "Valeur", "Commentaire / Règle de cohérence"]
        for col_idx, h in enumerate(headers_ctrl, start=1):
            cell = ws.cell(row=8, column=col_idx, value=h)
            appliquer_style_entete(cell)

        lignes_ctrl = [
            ("Nombre de lignes du journal", controles.nb_lignes_journal, FORMAT_NOMBRE_ENTIER, "Lignes arrhes du journal comptable"),
            ("Nombre de transactions OM", controles.nb_transactions_om, FORMAT_NOMBRE_ENTIER, "Transactions relevé Orange Money du jour"),
            ("Total Journal (Arrhes)", float(controles.total_journal), FORMAT_MONTANT_FCFA, "Total arrhes déposées"),
            ("Total Orange Money", float(controles.total_om), FORMAT_MONTANT_FCFA, "Total encaissements relevé OM"),
            ("Total Rapproché", float(controles.total_rapproche), FORMAT_MONTANT_FCFA, "Arrhes avec encaissement OM confirmé"),
            ("Total Recette du Jour", float(controles.total_recette_du_jour), FORMAT_MONTANT_FCFA, "Encaissements OM ordinaires (hors arrhes)"),
            ("Total Non Rapproché", float(controles.total_non_rapproche), FORMAT_MONTANT_FCFA, "Arrhes sans OM + recette du jour"),
            ("Montant des Écarts", float(controles.montant_ecarts), FORMAT_MONTANT_FCFA, "Écarts de montant sur appariements"),
            ("Taux de Rapprochement", controles.taux_rapprochement / 100.0, FORMAT_POURCENTAGE, "Couverture arrhes rapprochées / journal"),
            ("Conformités (Exactes)", controles.nb_conformites, FORMAT_NOMBRE_ENTIER, "Appariements sans aucun écart"),
            ("Manquants", controles.nb_manquants, FORMAT_NOMBRE_ENTIER, "Arrhes sans flux OM ou OM sans journal"),
            ("Doublons détectés", controles.nb_doublons, FORMAT_NOMBRE_ENTIER, "Doublons potentiels journal ou relevé"),
            ("Anomalies bloquantes", controles.nb_anomalies, FORMAT_NOMBRE_ENTIER, "Lignes exigeant une décision avant export"),
            ("Total Commissions OM", float(controles.total_commissions), FORMAT_MONTANT_FCFA, "Frais prélevés à la transaction (suivis à part)"),
        ]

        curr_row = 9
        for idx, (label, val, fmt, obs) in enumerate(lignes_ctrl):
            is_even = idx % 2 == 1
            c1 = ws.cell(row=curr_row, column=1, value=label)
            c2 = ws.cell(row=curr_row, column=2, value=val)
            c3 = ws.cell(row=curr_row, column=3, value=obs)

            appliquer_style_donnees(c1, is_even=is_even, is_bold=True)
            appliquer_style_donnees(c2, is_even=is_even, align=ALIGN_RIGHT)
            c2.number_format = fmt
            appliquer_style_donnees(c3, is_even=is_even, align=ALIGN_LEFT)
            curr_row += 1

        # Section 2 : Ventilation par Compte OM / Point de Vente
        curr_row += 2
        ws.cell(row=curr_row, column=1, value="2. Ventilation par Point de Vente / Compte Orange Money").font = FONT_SECTION
        curr_row += 1

        headers_vent = [
            "Compte OM",
            "Point de Vente / Intitulé",
            "Transactions",
            "Volume OM",
            "Volume Rapproché",
            "Recette du Jour",
            "Commissions",
            "Taux Rapprochement",
        ]
        for col_idx, h in enumerate(headers_vent, start=1):
            cell = ws.cell(row=curr_row, column=col_idx, value=h)
            appliquer_style_entete(cell)

        curr_row += 1
        start_vent_row = curr_row
        for idx, v in enumerate(synthese.ventilation_comptes):
            is_even = idx % 2 == 1
            ws.cell(row=curr_row, column=1, value=v.compte)
            ws.cell(row=curr_row, column=2, value=v.intitule)
            ws.cell(row=curr_row, column=3, value=v.nb_transactions).number_format = FORMAT_NOMBRE_ENTIER
            ws.cell(row=curr_row, column=4, value=float(v.total_om)).number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=5, value=float(v.total_rapproche)).number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=6, value=float(v.total_recette)).number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=7, value=float(v.total_commissions)).number_format = FORMAT_MONTANT_FCFA
            c8 = ws.cell(row=curr_row, column=8, value=v.taux_rapprochement / 100.0)
            c8.number_format = FORMAT_POURCENTAGE

            for c in range(1, 9):
                cell = ws.cell(row=curr_row, column=c)
                align = ALIGN_RIGHT if c >= 3 else (ALIGN_CENTER if c == 1 else ALIGN_LEFT)
                appliquer_style_donnees(cell, is_even=is_even, align=align)
            curr_row += 1

        # Ligne de total ventilation
        if synthese.ventilation_comptes:
            ws.cell(row=curr_row, column=1, value="TOTAL")
            ws.cell(row=curr_row, column=2, value="Ensemble des comptes")
            ws.cell(row=curr_row, column=3, value=f"=SUM(C{start_vent_row}:C{curr_row-1})").number_format = FORMAT_NOMBRE_ENTIER
            ws.cell(row=curr_row, column=4, value=f"=SUM(D{start_vent_row}:D{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=5, value=f"=SUM(E{start_vent_row}:E{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=6, value=f"=SUM(F{start_vent_row}:F{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=7, value=f"=SUM(G{start_vent_row}:G{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=8, value=f"=IF(D{curr_row}>0, E{curr_row}/D{curr_row}, 0)").number_format = FORMAT_POURCENTAGE

            for c in range(1, 9):
                cell = ws.cell(row=curr_row, column=c)
                cell.font = FONT_DATA_BOLD
                cell.fill = FILL_TOTAL
                cell.border = BORDER_TOP_BOTTOM_DOUBLE
                cell.alignment = ALIGN_RIGHT if c >= 3 else (ALIGN_CENTER if c == 1 else ALIGN_LEFT)

        ajuster_largeurs_colonnes(ws)

    # --------------------------------------------------------------------------
    # 2. Feuille Rapprochement
    # --------------------------------------------------------------------------
    def _creer_feuille_rapprochement(self, wb: openpyxl.Workbook, tables_lignes: list[LigneRapprochement]):
        ws = wb.create_sheet(title="Rapprochement")
        ws.views.sheetView[0].showGridLines = True
        ws.freeze_panes = "A2"

        headers = [
            "Date Opération",
            "Référence",
            "Client / Correspondant",
            "Montant Journal",
            "Montant OM",
            "Écart",
            "Statut",
            "Observation",
            "Niveau",
            "Compte OM",
        ]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            appliquer_style_entete(cell)

        curr_row = 2
        for idx, ligne in enumerate(tables_lignes):
            is_even = idx % 2 == 1
            date_str = ligne.date_operation.strftime("%d/%m/%Y") if ligne.date_operation else ""
            c_date = ws.cell(row=curr_row, column=1, value=date_str)
            c_ref = ws.cell(row=curr_row, column=2, value=ligne.reference)
            c_cli = ws.cell(row=curr_row, column=3, value=ligne.client)
            c_mj = ws.cell(row=curr_row, column=4, value=float(ligne.montant_journal))
            c_mom = ws.cell(row=curr_row, column=5, value=float(ligne.montant_om))
            c_ec = ws.cell(row=curr_row, column=6, value=float(ligne.ecart))
            c_stat = ws.cell(row=curr_row, column=7, value=ligne.statut.value)
            c_obs = ws.cell(row=curr_row, column=8, value=ligne.observation)
            niv_str = str(ligne.niveau) if ligne.niveau is not None else ""
            c_niv = ws.cell(row=curr_row, column=9, value=niv_str)
            c_cpt = ws.cell(row=curr_row, column=10, value=ligne.compte_om)

            # Styles
            for col_i, c in enumerate([c_date, c_ref, c_cli, c_mj, c_mom, c_ec, None, c_obs, c_niv, c_cpt], start=1):
                if c is not None:
                    align = ALIGN_RIGHT if col_i in (4, 5, 6) else (ALIGN_CENTER if col_i in (1, 9, 10) else ALIGN_LEFT)
                    appliquer_style_donnees(c, is_even=is_even, align=align)
                    if col_i in (4, 5, 6):
                        c.number_format = FORMAT_MONTANT_FCFA

            appliquer_style_statut(c_stat, ligne.statut)
            curr_row += 1

        # Ligne de totaux
        if tables_lignes:
            ws.cell(row=curr_row, column=1, value="TOTAL")
            ws.cell(row=curr_row, column=4, value=f"=SUM(D2:D{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=5, value=f"=SUM(E2:E{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=6, value=f"=SUM(F2:F{curr_row-1})").number_format = FORMAT_MONTANT_FCFA

            for c in range(1, 11):
                cell = ws.cell(row=curr_row, column=c)
                cell.font = FONT_DATA_BOLD
                cell.fill = FILL_TOTAL
                cell.border = BORDER_TOP_BOTTOM_DOUBLE
                if c in (4, 5, 6):
                    cell.alignment = ALIGN_RIGHT

        ws.auto_filter.ref = f"A1:J{max(curr_row-1, 1)}"
        ajuster_largeurs_colonnes(ws)

    # --------------------------------------------------------------------------
    # 3. Feuille Anomalies
    # --------------------------------------------------------------------------
    def _creer_feuille_anomalies(self, wb: openpyxl.Workbook, tables_lignes: list[LigneRapprochement]):
        ws = wb.create_sheet(title="Anomalies")
        ws.views.sheetView[0].showGridLines = True
        ws.freeze_panes = "A2"

        headers = [
            "Date",
            "Référence",
            "Client / Correspondant",
            "Montant Journal",
            "Montant OM",
            "Écart",
            "Statut",
            "Observation / Action requise",
            "Compte OM",
        ]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            appliquer_style_entete(cell)

        anomalies = extraire_anomalies(tables_lignes)
        curr_row = 2

        if not anomalies:
            cell = ws.cell(row=2, column=1, value="Aucune anomalie détectée sur cette période.")
            cell.font = FONT_DATA
            ws.merge_cells("A2:I2")
            curr_row = 3
        else:
            for idx, ligne in enumerate(anomalies):
                is_even = idx % 2 == 1
                date_str = ligne.date_operation.strftime("%d/%m/%Y") if ligne.date_operation else ""
                ws.cell(row=curr_row, column=1, value=date_str)
                ws.cell(row=curr_row, column=2, value=ligne.reference)
                ws.cell(row=curr_row, column=3, value=ligne.client)
                ws.cell(row=curr_row, column=4, value=float(ligne.montant_journal)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=5, value=float(ligne.montant_om)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=6, value=float(ligne.ecart)).number_format = FORMAT_MONTANT_FCFA
                c_stat = ws.cell(row=curr_row, column=7, value=ligne.statut.value)
                ws.cell(row=curr_row, column=8, value=ligne.observation)
                ws.cell(row=curr_row, column=9, value=ligne.compte_om)

                for col_i in [1, 2, 3, 4, 5, 6, 8, 9]:
                    cell = ws.cell(row=curr_row, column=col_i)
                    align = ALIGN_RIGHT if col_i in (4, 5, 6) else (ALIGN_CENTER if col_i in (1, 9) else ALIGN_LEFT)
                    appliquer_style_donnees(cell, is_even=is_even, align=align)

                appliquer_style_statut(c_stat, ligne.statut)
                curr_row += 1

            # Ligne de total
            ws.cell(row=curr_row, column=1, value="TOTAL ANOMALIES")
            ws.cell(row=curr_row, column=4, value=f"=SUM(D2:D{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=5, value=f"=SUM(E2:E{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=6, value=f"=SUM(F2:F{curr_row-1})").number_format = FORMAT_MONTANT_FCFA

            for c in range(1, 10):
                cell = ws.cell(row=curr_row, column=c)
                cell.font = FONT_DATA_BOLD
                cell.fill = FILL_TOTAL
                cell.border = BORDER_TOP_BOTTOM_DOUBLE
                if c in (4, 5, 6):
                    cell.alignment = ALIGN_RIGHT

        ws.auto_filter.ref = f"A1:I{max(curr_row-1, 1)}"
        ajuster_largeurs_colonnes(ws)

    # --------------------------------------------------------------------------
    # 4. Feuille Manquants_Journal
    # --------------------------------------------------------------------------
    def _creer_feuille_manquants_journal(
        self,
        wb: openpyxl.Workbook,
        tables_lignes: list[LigneRapprochement],
        resultats: list[ResultatRapprochement],
    ):
        ws = wb.create_sheet(title="Manquants_Journal")
        ws.views.sheetView[0].showGridLines = True
        ws.freeze_panes = "A2"

        headers = [
            "Date",
            "Heure",
            "Référence OM",
            "Compte Agent",
            "Correspondant (Client)",
            "Montant OM",
            "Commission",
            "Statut / Observation",
        ]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            appliquer_style_entete(cell)

        # Les manquants au journal peuvent être des transactions explicitement MANQUANT_JOURNAL
        # ou les encaissements de recette_du_jour selon la vue
        lignes_mj = extraire_manquants_journal(tables_lignes)
        recettes = [t for r in resultats for t in r.recette_du_jour]

        curr_row = 2
        if not lignes_mj and not recettes:
            cell = ws.cell(row=2, column=1, value="Aucun flux Orange Money sans contrepartie identifiée.")
            cell.font = FONT_DATA
            ws.merge_cells("A2:H2")
            curr_row = 3
        else:
            # Afficher d'abord les manquants stricts s'il y en a
            idx = 0
            for ligne in lignes_mj:
                is_even = idx % 2 == 1
                date_str = ligne.date_operation.strftime("%d/%m/%Y") if ligne.date_operation else ""
                ws.cell(row=curr_row, column=1, value=date_str)
                ws.cell(row=curr_row, column=2, value="")
                ws.cell(row=curr_row, column=3, value=ligne.reference)
                ws.cell(row=curr_row, column=4, value=ligne.compte_om)
                ws.cell(row=curr_row, column=5, value=ligne.client)
                ws.cell(row=curr_row, column=6, value=float(ligne.montant_om)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=7, value=float(ligne.commission)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=8, value=ligne.observation)

                for col_i in range(1, 9):
                    cell = ws.cell(row=curr_row, column=col_i)
                    align = ALIGN_RIGHT if col_i in (6, 7) else (ALIGN_CENTER if col_i in (1, 2, 4) else ALIGN_LEFT)
                    appliquer_style_donnees(cell, is_even=is_even, align=align)
                curr_row += 1
                idx += 1

            # Afficher les encaissements de la recette du jour
            for t in recettes:
                is_even = idx % 2 == 1
                date_str = t.date_operation.strftime("%d/%m/%Y") if t.date_operation else ""
                heure_str = t.heure.strftime("%H:%M:%S") if t.heure else ""
                ws.cell(row=curr_row, column=1, value=date_str)
                ws.cell(row=curr_row, column=2, value=heure_str)
                ws.cell(row=curr_row, column=3, value=t.reference)
                ws.cell(row=curr_row, column=4, value=t.compte_agent)
                ws.cell(row=curr_row, column=5, value=t.correspondant)
                ws.cell(row=curr_row, column=6, value=float(t.montant)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=7, value=float(t.commission)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=8, value="Recette ordinaire du jour (hors journal des arrhes)")

                for col_i in range(1, 9):
                    cell = ws.cell(row=curr_row, column=col_i)
                    align = ALIGN_RIGHT if col_i in (6, 7) else (ALIGN_CENTER if col_i in (1, 2, 4) else ALIGN_LEFT)
                    appliquer_style_donnees(cell, is_even=is_even, align=align)
                curr_row += 1
                idx += 1

            # Ligne de total
            ws.cell(row=curr_row, column=1, value="TOTAL")
            ws.cell(row=curr_row, column=6, value=f"=SUM(F2:F{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=7, value=f"=SUM(G2:G{curr_row-1})").number_format = FORMAT_MONTANT_FCFA

            for c in range(1, 9):
                cell = ws.cell(row=curr_row, column=c)
                cell.font = FONT_DATA_BOLD
                cell.fill = FILL_TOTAL
                cell.border = BORDER_TOP_BOTTOM_DOUBLE
                if c in (6, 7):
                    cell.alignment = ALIGN_RIGHT

        ws.auto_filter.ref = f"A1:H{max(curr_row-1, 1)}"
        ajuster_largeurs_colonnes(ws)

    # --------------------------------------------------------------------------
    # 5. Feuille Manquants_OM
    # --------------------------------------------------------------------------
    def _creer_feuille_manquants_om(self, wb: openpyxl.Workbook, tables_lignes: list[LigneRapprochement]):
        ws = wb.create_sheet(title="Manquants_OM")
        ws.views.sheetView[0].showGridLines = True
        ws.freeze_panes = "A2"

        headers = [
            "Ligne Source",
            "Date",
            "Client",
            "Réservation / Référence",
            "Montant Journal",
            "Statut",
            "Observation / Motif d'anomalie",
        ]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            appliquer_style_entete(cell)

        manquants = extraire_manquants_om(tables_lignes)
        curr_row = 2

        if not manquants:
            cell = ws.cell(row=2, column=1, value="Toutes les arrhes du journal ont trouvé leur encaissement Orange Money.")
            cell.font = FONT_DATA
            ws.merge_cells("A2:G2")
            curr_row = 3
        else:
            for idx, ligne in enumerate(manquants):
                is_even = idx % 2 == 1
                date_str = ligne.date_operation.strftime("%d/%m/%Y") if ligne.date_operation else ""
                ws.cell(row=curr_row, column=1, value=ligne.ligne_source or "")
                ws.cell(row=curr_row, column=2, value=date_str)
                ws.cell(row=curr_row, column=3, value=ligne.client)
                ws.cell(row=curr_row, column=4, value=ligne.reference)
                ws.cell(row=curr_row, column=5, value=float(ligne.montant_journal)).number_format = FORMAT_MONTANT_FCFA
                c_stat = ws.cell(row=curr_row, column=6, value=ligne.statut.value)
                ws.cell(row=curr_row, column=7, value=ligne.observation)

                for col_i in [1, 2, 3, 4, 5, 7]:
                    cell = ws.cell(row=curr_row, column=col_i)
                    align = ALIGN_RIGHT if col_i == 5 else (ALIGN_CENTER if col_i in (1, 2) else ALIGN_LEFT)
                    appliquer_style_donnees(cell, is_even=is_even, align=align)

                appliquer_style_statut(c_stat, ligne.statut)
                curr_row += 1

            # Ligne de total
            ws.cell(row=curr_row, column=1, value="TOTAL")
            ws.cell(row=curr_row, column=5, value=f"=SUM(E2:E{curr_row-1})").number_format = FORMAT_MONTANT_FCFA

            for c in range(1, 8):
                cell = ws.cell(row=curr_row, column=c)
                cell.font = FONT_DATA_BOLD
                cell.fill = FILL_TOTAL
                cell.border = BORDER_TOP_BOTTOM_DOUBLE
                if c == 5:
                    cell.alignment = ALIGN_RIGHT

        ws.auto_filter.ref = f"A1:G{max(curr_row-1, 1)}"
        ajuster_largeurs_colonnes(ws)

    # --------------------------------------------------------------------------
    # 6. Feuille Doublons
    # --------------------------------------------------------------------------
    def _creer_feuille_doublons(self, wb: openpyxl.Workbook, resultats: list[ResultatRapprochement]):
        ws = wb.create_sheet(title="Doublons")
        ws.views.sheetView[0].showGridLines = True

        # Section 1 : Doublons Journal
        ws.cell(row=1, column=1, value="1. Doublons détectés dans le Journal des Arrhes").font = FONT_SECTION

        headers_dj = ["Ligne Source", "Date", "Client", "Réservation", "Montant", "Statut Doublon"]
        for col_idx, h in enumerate(headers_dj, start=1):
            cell = ws.cell(row=2, column=col_idx, value=h)
            appliquer_style_entete(cell)

        tous_dj = [ligne for r in resultats for ligne in r.doublons_journal]
        curr_row = 3

        if not tous_dj:
            c = ws.cell(row=3, column=1, value="Aucun doublon détecté dans le journal des arrhes.")
            c.font = FONT_DATA
            ws.merge_cells("A3:F3")
            curr_row = 4
        else:
            for idx, dj in enumerate(tous_dj):
                is_even = idx % 2 == 1
                date_str = dj.jour.strftime("%d/%m/%Y") if dj.jour else ""
                ws.cell(row=curr_row, column=1, value=dj.ligne_source)
                ws.cell(row=curr_row, column=2, value=date_str)
                ws.cell(row=curr_row, column=3, value=dj.client)
                ws.cell(row=curr_row, column=4, value=dj.reference_interne)
                ws.cell(row=curr_row, column=5, value=float(dj.montant)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=6, value="Doublon potentiel journal")

                for col_i in range(1, 7):
                    cell = ws.cell(row=curr_row, column=col_i)
                    align = ALIGN_RIGHT if col_i == 5 else (ALIGN_CENTER if col_i in (1, 2) else ALIGN_LEFT)
                    appliquer_style_donnees(cell, is_even=is_even, align=align)
                curr_row += 1

        # Section 2 : Doublons Orange Money
        curr_row += 2
        ws.cell(row=curr_row, column=1, value="2. Doublons détectés dans le Relevé Orange Money").font = FONT_SECTION
        curr_row += 1

        headers_dom = ["Date", "Heure", "Référence OM", "Compte Agent", "Correspondant", "Montant OM", "Statut Doublon"]
        for col_idx, h in enumerate(headers_dom, start=1):
            cell = ws.cell(row=curr_row, column=col_idx, value=h)
            appliquer_style_entete(cell)

        curr_row += 1
        tous_dom = [t for r in resultats for t in r.doublons_om]

        if not tous_dom:
            c = ws.cell(row=curr_row, column=1, value="Aucun doublon détecté dans les encaissements Orange Money.")
            c.font = FONT_DATA
            ws.merge_cells(f"A{curr_row}:G{curr_row}")
            curr_row += 1
        else:
            for idx, dom in enumerate(tous_dom):
                is_even = idx % 2 == 1
                date_str = dom.date_operation.strftime("%d/%m/%Y") if dom.date_operation else ""
                heure_str = dom.heure.strftime("%H:%M:%S") if dom.heure else ""
                ws.cell(row=curr_row, column=1, value=date_str)
                ws.cell(row=curr_row, column=2, value=heure_str)
                ws.cell(row=curr_row, column=3, value=dom.reference)
                ws.cell(row=curr_row, column=4, value=dom.compte_agent)
                ws.cell(row=curr_row, column=5, value=dom.correspondant)
                ws.cell(row=curr_row, column=6, value=float(dom.montant)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=7, value="Doublon potentiel relevé OM")

                for col_i in range(1, 8):
                    cell = ws.cell(row=curr_row, column=col_i)
                    align = ALIGN_RIGHT if col_i == 6 else (ALIGN_CENTER if col_i in (1, 2, 4) else ALIGN_LEFT)
                    appliquer_style_donnees(cell, is_even=is_even, align=align)
                curr_row += 1

        ajuster_largeurs_colonnes(ws)

    # --------------------------------------------------------------------------
    # 7. Feuille Contrôle_Mensuel
    # --------------------------------------------------------------------------
    def _creer_feuille_controle_mensuel(self, wb: openpyxl.Workbook, synthese: SyntheseMensuelle):
        ws = wb.create_sheet(title="Contrôle_Mensuel")
        ws.views.sheetView[0].showGridLines = True
        ws.freeze_panes = "A2"

        headers = [
            "Date",
            "Lignes Journal",
            "Total Arrhes",
            "Transactions OM",
            "Total OM",
            "Total Rapproché",
            "Recette du Jour",
            "Écarts Constatés",
            "Statut Journée",
        ]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            appliquer_style_entete(cell)

        curr_row = 2
        start_data_row = curr_row

        if not synthese.details_journaliers:
            cell = ws.cell(row=2, column=1, value="Aucun historique journalier disponible.")
            cell.font = FONT_DATA
            ws.merge_cells("A2:I2")
            curr_row = 3
        else:
            for idx, dj in enumerate(synthese.details_journaliers):
                is_even = idx % 2 == 1
                date_str = dj.jour.strftime("%d/%m/%Y") if dj.jour else ""
                ws.cell(row=curr_row, column=1, value=date_str)
                ws.cell(row=curr_row, column=2, value=dj.nb_arrhes).number_format = FORMAT_NOMBRE_ENTIER
                ws.cell(row=curr_row, column=3, value=float(dj.total_arrhes)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=4, value=dj.nb_om).number_format = FORMAT_NOMBRE_ENTIER
                ws.cell(row=curr_row, column=5, value=float(dj.total_om)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=6, value=float(dj.total_rapproche)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=7, value=float(dj.total_recette)).number_format = FORMAT_MONTANT_FCFA
                ws.cell(row=curr_row, column=8, value=float(dj.total_ecarts)).number_format = FORMAT_MONTANT_FCFA

                c_stat = ws.cell(row=curr_row, column=9, value=dj.statut_global)
                if dj.statut_global == "CONFORME":
                    c_stat.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                    c_stat.font = Font(name="Calibri", size=10, bold=True, color="166534")
                else:
                    c_stat.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                    c_stat.font = Font(name="Calibri", size=10, bold=True, color="92400E")
                c_stat.alignment = ALIGN_CENTER
                c_stat.border = BORDER_THIN

                for col_i in range(1, 9):
                    cell = ws.cell(row=curr_row, column=col_i)
                    align = ALIGN_RIGHT if col_i in (2, 3, 4, 5, 6, 7, 8) else ALIGN_CENTER
                    appliquer_style_donnees(cell, is_even=is_even, align=align)
                curr_row += 1

            # Ligne de cumul / total
            ws.cell(row=curr_row, column=1, value="CUMUL PÉRIODE")
            ws.cell(row=curr_row, column=2, value=f"=SUM(B{start_data_row}:B{curr_row-1})").number_format = FORMAT_NOMBRE_ENTIER
            ws.cell(row=curr_row, column=3, value=f"=SUM(C{start_data_row}:C{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=4, value=f"=SUM(D{start_data_row}:D{curr_row-1})").number_format = FORMAT_NOMBRE_ENTIER
            ws.cell(row=curr_row, column=5, value=f"=SUM(E{start_data_row}:E{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=6, value=f"=SUM(F{start_data_row}:F{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=7, value=f"=SUM(G{start_data_row}:G{curr_row-1})").number_format = FORMAT_MONTANT_FCFA
            ws.cell(row=curr_row, column=8, value=f"=SUM(H{start_data_row}:H{curr_row-1})").number_format = FORMAT_MONTANT_FCFA

            total_anomalies = synthese.controles_globaux.nb_anomalies
            statut_cumul = "CONFORME" if total_anomalies == 0 else "À CONTRÔLER"
            ws.cell(row=curr_row, column=9, value=statut_cumul)

            for c in range(1, 10):
                cell = ws.cell(row=curr_row, column=c)
                cell.font = FONT_DATA_BOLD
                cell.fill = FILL_TOTAL
                cell.border = BORDER_TOP_BOTTOM_DOUBLE
                if c >= 2 and c <= 8:
                    cell.alignment = ALIGN_RIGHT
                else:
                    cell.alignment = ALIGN_CENTER

        ws.auto_filter.ref = f"A1:I{max(curr_row-1, 1)}"
        ajuster_largeurs_colonnes(ws)
