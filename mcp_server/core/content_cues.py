"""Language-aware decision / error / success cue detection.

source: ADR-0137
"""

from __future__ import annotations

import re

# ── Structural error markers (language-agnostic, case-sensitive) ──────────
# Runtime-emitted shapes; the author's natural language never changes them.
_STRUCTURAL_ERROR_PATTERNS: tuple[str, ...] = (
    # source: ADR-0137
    r"Traceback \(most recent call last\)",
    # source: ADR-0137
    r"File \"[^\"]+\", line \d+",
    # source: ADR-0137
    r"\bat [^\s(]+ ?\([^()]*:\d+(?::\d+)?\)",
    # source: ADR-0137
    r"\b[A-Z][A-Za-z0-9]*(?:Error|Exception)\b",
    # source: ADR-0137
    r"\bSIG(?:SEGV|ABRT|BUS|FPE|ILL|KILL|TERM)\b",
)

# source: ADR-0137

_DECISION_PATTERNS: dict[str, str] = {
    # source: ADR-0137
    "en": r"\b(?:decided|chose|switched|migrated|selected|picked|opted)\b",
    # es: decidí/decidimos/decidido, decisión, elegí/elegimos/elegido,
    #     eligió, escogimos/escogido, optamos/opté/optó/optado,
    #     seleccionó/seleccionado, cambiamos/cambié/cambió (switched)  # noqa: ERA001
    "es": (
        r"\bdecid\w*|\bdecisi[oó]n\w*|\beleg[ií]\w*|\beligi\w*|\bescog\w*"
        r"|\bopt(?:amos|é|ó|ado|aron)\b|\bseleccion\w*"
        r"|\bcambi(?:amos|é|ó)\b"
    ),
    # pt: decidimos/decidiu/decidido, decisão/decisões, escolhemos/escolhido/
    #     escolha, optamos/optou/optado, selecionou/selecionado,
    #     migramos/migrou/migrado, mudamos (switched)  # noqa: ERA001
    "pt": (
        r"\bdecid\w*|\bdecis[aã]o\b|\bdecis[oõ]es\b|\bescolh\w*"
        r"|\bopt(?:amos|ou|ado|aram)\b|\bselecion\w*"
        r"|\bmigr(?:amos|ou|ado|aram)\b|\bmudamos\b"
    ),
    # fr: décidé/décidons (accented or not), décision, choisi/choisie/
    #     choisissons, opté, sélectionné, migré/migration,
    #     basculé (switched)  # noqa: ERA001 -- multi-language prose gloss, not code
    "fr": (
        r"\bd[ée]cid\w*|\bd[ée]cisi\w*|\bchoisi\w*|\bopt[ée]\b"
        r"|\bs[ée]lectionn\w*|\bmigr[ée]\w*|\bbascul[ée]\w*"
    ),
    # de: entschied/entschieden, Entscheidung, gewählt, ausgewählt,
    #     entschlossen, migriert, gewechselt/umgestiegen (switched)  # noqa: ERA001
    "de": (
        r"\bentschied\w*|\bentscheidung\w*|\bgew[äa]hlt\b|\bausgew[äa]hlt\b"
        r"|\bentschlossen\b|\bmigriert\w*|\bgewechselt\b|\bumgestiegen\b"
    ),
    # ru: решил/решили/решено/решение, выбрал/выбрали/выбрано, выбор,
    #     перешёл/перешли (switched to), мигрировали
    "ru": (
        r"\bреши\w*|\bрешен\w*|\bрешён\w*|\bвыбр\w*|\bвыбор\w*"
        r"|\bпереш[её]л\w*|\bперешли\b|\bмигрир\w*"
    ),
    # source: ADR-0137
    "ja": r"決定|決め|選択|選ん|選び|採用|移行",
    # source: ADR-0137
    "ro": (
        r"\bdecis\w*|\bdecid\w*|\bdecizi\w*|\bales\b|\baleas[aă]\b"
        r"|\baleg\w*|\boptat\b|\bopt[aă]m\b|\bmigrat\w*"
    ),
}

# ── Error cues ─────────────────────────────────────────────────────────────
_ERROR_PATTERNS: dict[str, str] = {
    # source: ADR-0137
    "en": (
        r"\b(?:error|exception|traceback|failed|failure|bug|crash|broken|"
        r"timeout|denied|rejected|deprecated)\b"
    ),
    # es: excepción, falla/fallo/falló/fallado/fallando/fallaron/fallamos,
    #     roto/rota (broken), rechazado, caída (crash/outage).
    #     "error" is identical in Spanish — already covered by en.
    #     Collision note: \brota\b also matches BrE "rota" (schedule) —
    #     accepted (recall bias).
    "es": (
        r"\bexcepci[oó]n\w*|\bfall(?:[aoó]|ad[oa]s?|ando|aron|amos)\b"
        r"|\brot[oa]s?\b|\brechazad\w*|\bca[ií]da\b"
    ),
    # pt: erro(s), exceção/exceções, falha/falhou/falhado, quebrado (broken),
    #     rejeitado, travou (froze/crashed)  # noqa: ERA001 -- language gloss, not code
    "pt": (
        r"\berros?\b|\bexce[çc][aã]o\w*|\bexce[çc][oõ]es\b|\bfalh\w*"
        r"|\bquebrad\w*|\brejeitad\w*|\btravou\b"
    ),
    # fr: erreur(s), échec(s), échoué/échouons (accented or not),
    #     rejeté, cassé/cassée(s) (broken), expiré (timed out).
    #     "exception" is identical in French — already covered by en.
    "fr": (
        r"\berreurs?\b|\b[ée]checs?\b|\b[ée]chou\w*|\brejet[ée]\w*"
        r"|\bcass[ée]e?s?\b|\bexpir[ée]\w*"
    ),
    # de: Fehler(-meldung), fehlgeschlagen/Fehlschlag, Ausnahme,
    #     Absturz/abgestürzt, kaputt, abgelehnt, defekt
    "de": (
        r"\bfehler\w*|\bfehlgeschlagen\b|\bfehlschlag\w*|\bausnahme\w*"
        r"|\babsturz\w*|\babgest[üu]rzt\b|\bkaputt\b|\babgelehnt\b|\bdefekt\w*"
    ),
    # ru: ошибка/ошибки/ошибок/ошибся, исключение, сбой/сбоя/сбои,
    #     не удалось (failed to), упал/упало (crashed), сломался (broke),
    #     отклонен/отклонён, таймаут/тайм-аут
    "ru": (
        r"\bошиб\w*|\bисключени\w*|\bсбо[йяие]\w*|\bне удалось\b"
        r"|\bупал[оаи]?\b|\bслома\w*|\bотклонен\w*|\bотклонён\w*"
        r"|\bтайм-?аут\w*"
    ),
    # source: ADR-0137
    "ja": r"エラー|例外|失敗|バグ|クラッシュ|タイムアウト|拒否|壊れ|不具合",
    # ro: eroare/erori, excepție/excepția, eșuat/eșec (accented or not),
    #     defect, stricat (broken), respins (rejected),  # noqa: ERA001 -- gloss
    #     căzut (crashed/down)  # noqa: ERA001 -- language gloss, not code
    "ro": (
        r"\beroare\b|\berori\w*|\bexcep[țt]i\w*|\be[șs]uat\w*|\be[șs]ec\w*"
        r"|\bdefect\w*|\bstricat\w*|\brespins\w*|\bc[ăa]zut\w*"
    ),
}

# ── Success cues ───────────────────────────────────────────────────────────
_SUCCESS_PATTERNS: dict[str, str] = {
    # source: ADR-0137
    "en": r"\b(?:fixed|resolved|succeeded|passed|completed|done)\b",
    # es: arreglado/arreglamos/arreglé, resuelto/resolvimos, éxito/exitoso,
    #     completado, corregido/corregimos, funcionó, aprobado (passed),  # noqa: ERA001
    #     terminado
    "es": (
        r"\barregl\w*|\bresuelt\w*|\bresolvi\w*|\b[ée]xito\w*|\bexitos\w*"
        r"|\bcompletad\w*|\bcorregid\w*|\bcorregimos\b|\bfuncion[oó]\b"
        r"|\baprobad\w*|\bterminad\w*"
    ),
    # pt: consertado, corrigido, resolvido/resolvemos, sucesso(s),
    #     concluído, aprovado (passed), funcionou  # noqa: ERA001 -- gloss, not code
    "pt": (
        r"\bconsertad\w*|\bcorrigid\w*|\bresolvid\w*|\bresolvemos\b"
        r"|\bsucessos?\b|\bconclu[ií]d\w*|\baprovad\w*|\bfuncionou\b"
    ),
    # fr: corrigé, résolu, réussi, terminé, achevé, réparé
    #     (all with or without accents)
    "fr": (
        r"\bcorrig[ée]\w*|\br[ée]solu\w*|\br[ée]ussi\w*|\btermin[ée]\w*"
        r"|\bachev[ée]\w*|\br[ée]par[ée]\w*"
    ),
    # de: behoben, gelöst, erfolgreich, abgeschlossen, repariert,
    #     bestanden (passed), funktioniert  # noqa: ERA001 -- language gloss, not code
    "de": (
        r"\bbehoben\b|\bgel[öo]st\b|\berfolgreich\w*|\babgeschlossen\b"
        r"|\brepariert\w*|\bbestanden\b|\bfunktioniert\w*"
    ),
    # ru: исправил/исправлено/исправили, решено/решен (also "decided" —
    #     решить means both decide and solve; the overlap is inherent to the
    #     language and both cues bypass anyway), успешно/успех, завершено,
    #     починил, заработало (works now), готово (done)
    "ru": (
        r"\bисправ\w*|\bрешен\w*|\bрешён\w*|\bуспешн\w*|\bуспех\w*"
        r"|\bзаверш\w*|\bпочин\w*|\bзаработал\w*|\bготово\b"
    ),
    # source: ADR-0137
    "ja": r"修正|解決|成功|完了|直した|直しました",
    # ro: reparat, rezolvat/rezolvăm, reușit (accented or not), succes,
    #     finalizat, corectat, funcționează (it works)
    "ro": (
        r"\breparat\w*|\brezolvat\w*|\brezolv[aă]m\b|\breu[șs]it\w*"
        r"|\bsucces\w*|\bfinalizat\w*|\bcorectat\w*"
        r"|\bfunc[țt]ioneaz[ăa]\b"
    ),
}


def _compile_keyword_union(patterns: dict[str, str]) -> re.Pattern[str]:
    """Union of the per-language fragments, case-insensitive.

    IGNORECASE folds Latin and Cyrillic; it is a no-op for CJK.
    """
    return re.compile("|".join(patterns.values()), re.IGNORECASE)


_DECISION_RE = _compile_keyword_union(_DECISION_PATTERNS)
_ERROR_RE = _compile_keyword_union(_ERROR_PATTERNS)
_SUCCESS_RE = _compile_keyword_union(_SUCCESS_PATTERNS)
# source: ADR-0137
_STRUCTURAL_ERROR_RE = re.compile("|".join(_STRUCTURAL_ERROR_PATTERNS))


def is_decision_cue(content: str) -> bool:
    """True when content carries a decision cue in any covered language.

    source: ADR-0137
    """
    return bool(_DECISION_RE.search(content))


def is_error_cue(content: str) -> bool:
    """True on structural error markers (any language) or error keywords."""
    return bool(_STRUCTURAL_ERROR_RE.search(content) or _ERROR_RE.search(content))


def is_success_cue(content: str) -> bool:
    """True when content carries a success cue in any covered language."""
    return bool(_SUCCESS_RE.search(content))
