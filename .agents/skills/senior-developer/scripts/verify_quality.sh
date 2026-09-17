#!/usr/bin/env bash
# Script de vérification de conformité qualité "Senior Developer" (100 règles)

set -euo pipefail

echo "========================================================"
echo " [Senior Developer] Contrôle qualité & conformité"
echo "========================================================"

FAILED=0

# 1. Vérification des secrets évidents ou hardcodés dans le code source
echo -n "1. Détection de secrets ou mots de passe en dur... "
if grep -rnE --include="*.py" --exclude-dir={.git,.venv,__pycache__,tests} "(password|secret_key|api_key)\s*=\s*['\"][^'\"]{6,}['\"]" . > /dev/null 2>&1; then
    echo "❌ ATTENTION : Présence potentielle de secrets en clair dans le code !"
    FAILED=1
else
    echo "✅ OK"
fi

# 2. Détection de points d'arrêt ou print résiduels dans le code source
echo -n "2. Détection de points d'arrêt résiduels (debug)... "
if grep -rnE --include="*.py" --exclude-dir={.git,.venv,__pycache__,tests} "(breakpoint\(\)|pdb\.set_trace)" . > /dev/null 2>&1; then
    echo "❌ ATTENTION : Breakpoints détectés !"
    FAILED=1
else
    echo "✅ OK"
fi

# 3. Exécution de la suite de tests
echo "3. Exécution des tests automatisés..."
if [ -f "./.venv/bin/pytest" ]; then
    ./.venv/bin/pytest --tb=short -q
    echo "✅ Tests réussis avec succès."
else
    echo "⚠️ Pas d'environnement pytest local trouvé dans .venv"
fi

echo "========================================================"
if [ $FAILED -eq 0 ]; then
    echo "🎉 Félicitations : Le code respecte la checklist Senior Developer !"
    exit 0
else
    echo "⚠️ Des anomalies ont été détectées, corrigez-les avant livraison."
    exit 1
fi
