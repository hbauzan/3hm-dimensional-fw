#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "torch>=2.4.0",
#     "sentence-transformers>=3.2.0",
#     "numpy>=1.26.0",
# ]
# ///
"""Embed Suite 2 strings with BAAI/bge-m3 float32 vectors.

Reads JSON lines from `cargo run -p sf-bench --bin suite2_string_dump`.
Each line is a canonical seed sentence, or a normalized prompt or segmented
clause the Rust suite will score. This script does not split clauses.

English attacks in the suite catalog come from CLINC OOS (`oos_test`) and
English rows of the deepset prompt-injection set. Spanish seed domains use
Spanish clean queries and Spanish attacks. Measured rates are printed by the
Rust suite after this file is written.

Outputs:
- crates/sf-bench/fixtures/oos_bge_m3_vectors.bin
- crates/sf-bench/fixtures/oos_bge_m3_metadata.json
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

DIM = 1024

CANONICAL_DOMAINS = [
    "python",
    "receta",
    "legal",
    "medicina",
    "astronomia",
    "finanzas",
    "filosofia",
    "musica",
    "geologia",
    "botanica",
    "arquitectura",
]

# Seed sentences copied from crates/sf-bench/src/canonical_corpus.rs.
CANONICAL_SEED_SENTENCES = {
    "python": [
        "def quicksort(items: list[int]) -> list[int]: return items if len(items) < 2 else quicksort([x for x in items if x < items[0]]) + quicksort([x for x in items if x >= items[0]])",
        "A generator yields values lazily with yield inside a function that keeps its frame between iterations.",
        "asyncio.gather schedules coroutines on one event loop and awaits their results together.",
        "A dataclass with frozen=True stores configuration fields without a mutable __dict__.",
        "The walrus operator assigns inside a while condition when reading chunks from a binary file.",
        "typing.Protocol describes the methods a caller needs without forcing a nominal base class.",
        "pytest fixtures inject a temporary directory and tear it down after the test function returns.",
        "A context manager implemented with contextlib.contextmanager closes the socket on the way out.",
        "List comprehensions build a new list; generator expressions do not materialize every element.",
        "hashlib.sha256 updates a hasher with bytes and returns a hex digest.",
        "The descriptor protocol routes attribute access through __get__ and __set__ on the class.",
        "venv isolates a project interpreter so pip installs do not land in the system site-packages.",
        "struct.unpack reads a little-endian uint32 from a four-byte memoryview.",
        "functools.lru_cache memoizes a pure function and exposes cache_info for hit counts.",
        "A match statement discriminates on enum-like unions of tuples without a chain of isinstance.",
        "pathlib.Path.rglob walks a tree and yields Path objects rather than bare strings.",
    ],
    "receta": [
        "Sofreír la cebolla en aceite de oliva hasta que esté transparente antes de agregar el arroz.",
        "El risotto pide caldo caliente, incorporado de a un cucharón, hasta que el grano suelte el almidón.",
        "Para la salsa de tomate, cocinar a fuego bajo ajo, tomate perita y una hoja de laurel.",
        "Salpimentar el pollo y dorarlo en manteca antes de desglasarlo con vino blanco.",
        "La masa de pasta necesita harina 00, huevos y un reposo cubierto para que el gluten relaje.",
        "Blanquear las verduras en agua hirviendo con sal y cortar la cocción en un baño de hielo.",
        "Montar la manteca en la salsa fuera del fuego para emulsionar sin que se corte.",
        "El caldo de verduras lleva apio, zanahoria, puerro y una hora de cocción suave.",
        "Hornear el pan a 220 grados con vapor los primeros diez minutos para abrir la corteza.",
        "Reducir la crema con queso rallado hasta que napar la cuchara.",
        "Marinar el pescado con limón, ajo y perejil al menos veinte minutos antes de la plancha.",
        "La bechamel se liga con manteca y harina tostada, luego leche fría en hilo.",
        "Picar la albahaca a cuchillo y mezclarla con el pesto fuera del calor.",
        "Dejar reposar el guiso tapado para que el colágeno del osobuco espese el fondo.",
        "Caramelizar azúcar seco y bajarlo con vinagre para una gastrique de cebolla.",
        "Servir la receta con aceite de oliva crudo y pimienta recién molida.",
    ],
    "legal": [
        "El contrato de locación obliga al locatario a conservar la cosa y a pagar el canon en término.",
        "La cláusula penal liquida los daños previsibles cuando el incumplimiento es imputable.",
        "La demanda debe individualizar las partes, los hechos y el derecho en que se funda.",
        "El plazo de prescripción de la acción contractual corre desde que la obligación es exigible.",
        "La escritura pública da fecha cierta y legitima la tradición del inmueble.",
        "El recurso de apelación se concede en relación y con efecto devolutivo salvo norma especial.",
        "La cosa juzgada impide reeditar entre las mismas partes la pretensión ya decidida.",
        "El domicilio constituido en el expediente es el único válido para las notificaciones.",
        "La responsabilidad objetiva del guardián de la cosa riesgosa no exige culpa.",
        "El poder general para administrar no autoriza a enajenar ni a gravar.",
        "La mora del deudor se produce por interpelación fehaciente cuando el plazo no está determinado.",
        "El fideicomiso separa el patrimonio fideicomitido del patrimonio del fiduciario.",
        "La nulidad absoluta puede declararse de oficio cuando el acto lesiona el orden público.",
        "La competencia territorial del fuero civil se fija por el domicilio del demandado.",
        "La cláusula arbitral desplaza la jurisdicción judicial si el convenio es escrito y válido.",
        "La indemnización por despido sin causa incluye antigüedad, preaviso e integración del mes.",
    ],
    "medicina": [
        "La auscultación pulmonar busca crepitantes en bases como signo de edema alveolar.",
        "La dosis de amoxicilina en el adulto es de 500 mg cada ocho horas por vía oral.",
        "Un electrocardiograma con supradesnivel del ST en V2 a V4 sugiere oclusión de la descendente anterior.",
        "La gasometría arterial informa pH, PaO2, PaCO2 y bicarbonato para clasificar el trastorno ácido-base.",
        "La profilaxis de trombosis venosa profunda usa heparina de bajo peso molecular en el postoperatorio.",
        "La escala de Glasgow puntúa apertura ocular, respuesta verbal y respuesta motora.",
        "La creatinina sérica elevada con oliguria define una injuria renal aguda.",
        "El examen neurológico del reflejo rotuliano evalúa la raíz L4.",
        "La tomografía de tórax sin contraste muestra vidrio esmerilado periférico.",
        "La indicación de insulina basal se ajusta según la glucemia de ayuno.",
        "La asepsia del campo quirúrgico reduce la inoculación de flora cutánea.",
        "Un soplo holosistólico en foco mitral irradia a la axila.",
        "La rehidratación del cólera repone sodio y potasio con solución de la OMS.",
        "La biopsia informa márgenes libres cuando no hay células neoplásicas en el borde tintado.",
        "La saturación de oxígeno por pulsioximetría no distingue carboxihemoglobina.",
        "El consentimiento informado documenta riesgos, alternativas y la identidad del paciente.",
    ],
    "astronomia": [
        "El paralaje anual de una estrella cercana da su distancia en parsecs.",
        "La secuencia principal del diagrama de Hertzsprung-Russell concentra las estrellas que fusionan hidrógeno.",
        "Un tránsito exoplanetario baja el flujo de la estrella en proporción al área del disco ocultado.",
        "La ley de Hubble relaciona la velocidad de recesión con la distancia a la galaxia.",
        "El perihelio de Mercurio precesa por la curvatura del espacio-tiempo solar.",
        "Una supernova de tipo Ia sirve de candela estándar por su luminosidad calibrada.",
        "La metalicidad se expresa como la abundancia de hierro respecto del hidrógeno en escala logarítmica.",
        "El seeing limita la resolución de un telescopio terrestre por la turbulencia atmosférica.",
        "Los anillos de Saturno están compuestos de hielo de agua en órbitas keplerianas.",
        "El corrimiento al rojo cosmológico estira la longitud de onda de los fotones en vuelo.",
        "Una nebulosa planetaria es la envoltura ionizada que expulsa una estrella de masa baja.",
        "La magnitud aparente bolométrica integra el flujo en todas las longitudes de onda.",
        "El solsticio ocurre cuando la declinación del Sol alcanza su extremo.",
        "Un cuásar es el núcleo activo de una galaxia alimentado por acreción sobre un agujero negro.",
        "La curva de rotación plana de una galaxia espiral exige masa no luminosa.",
        "El espectro de absorción del hidrógeno muestra la serie de Balmer en el óptico.",
    ],
    "finanzas": [
        "El valor presente descuenta flujos futuros con una tasa que refleja el costo de capital.",
        "Un bono cupón cero cotiza bajo la par y su rendimiento es la TIR hasta el vencimiento.",
        "La duración de Macaulay mide la sensibilidad del precio del bono a la tasa de interés.",
        "El CAPM exige un retorno igual a la tasa libre de riesgo más beta por la prima de mercado.",
        "El EBITDA excluye intereses, impuestos y amortizaciones del resultado operativo.",
        "Una opción call europea se ejerce solo en la fecha de vencimiento.",
        "El spread de crédito es el exceso de rendimiento de un bono corporativo sobre el soberano.",
        "La volatilidad implícita es el sigma que iguala el precio de Black-Scholes al de mercado.",
        "El flujo de caja libre es el efectivo disponible después de reinversión y capital de trabajo.",
        "Una cobertura con futuros vende el contrato para fijar el precio de venta del subyacente.",
        "El ratio de liquidez corriente divide el activo corriente por el pasivo corriente.",
        "La amortización francesa mantiene la cuota constante y baja el interés con el saldo.",
        "El VaR al 99 por ciento estima la pérdida que no se supera en ese percentil histórico.",
        "Una acción preferida paga un dividendo fijo y tiene prioridad sobre la ordinaria en la liquidación.",
        "El tipo de cambio spot es el precio de contado de la divisa.",
        "La convexidad corrige la aproximación lineal de la duración cuando la tasa se mueve mucho.",
    ],
    "filosofia": [
        "El imperativo categórico ordena obrar solo según una máxima que pueda quererse como ley universal.",
        "La duda metódica suspende el asentimiento a toda creencia que no sea clara y distinta.",
        "Gettier mostró que la creencia verdadera justificada no basta para definir el conocimiento.",
        "El ser-ahí heideggeriano está arrojado al mundo y se comprende desde sus posibilidades.",
        "La falacia naturalista deduce un deber de un es sin una premisa normativa.",
        "El utilitarismo de actos evalúa cada acción por la utilidad total que produce.",
        "Quine atacó la distinción analítico-sintético como un dogma sin criterio empírico.",
        "La fenomenología describe la experiencia tal como se da, entre paréntesis la tesis del mundo.",
        "El contrato social de Rousseau funda la voluntad general en la alienación de cada asociado.",
        "Wittgenstein tardío trata el significado como el uso dentro de un juego de lenguaje.",
        "La identidad personal en Locke se ancla en la continuidad de la conciencia, no en la sustancia.",
        "Aristóteles define la virtud como un hábito electivo situado en el término medio.",
        "El falsacionismo exige que una teoría científica arriesgue predicciones que puedan fallar.",
        "La libertad negativa es la ausencia de interferencia externa en el ámbito de acción.",
        "Spinoza identifica a Dios con la sustancia única de infinitos atributos.",
        "El escepticismo pirrónico suspende el juicio ante la equipolencia de las apariencias.",
    ],
    "musica": [
        "Una cadencia auténtica perfecta resuelve el acorde de dominante en tónica en estado fundamental.",
        "El contrapunto de la primera especie enfrenta nota contra nota en consonancias.",
        "El compás de 6/8 agrupa dos pulsos ternarios y se dirige con un dos.",
        "La forma sonata expone dos temas, los desarrolla y los recapitula en la tónica.",
        "Un intervalo de tritono divide la octava en dos partes iguales y pide resolución.",
        "La dinámica pianissimo se escribe pp y pide un ataque apenas audible.",
        "El modo dórico tiene la tercera menor y la sexta mayor respecto de la tónica.",
        "Una fuga expone el sujeto en la tónica y la respuesta en la dominante.",
        "El vibrato es una oscilación periódica de la altura alrededor de la nota escrita.",
        "La armonía de cuarta suspendida reemplaza la tercera y resuelve descendentemente.",
        "Un cluster de tonos enteros evita el semitono y diluye la función tonal.",
        "La articulación staccato acorta la nota a una fracción de su valor escrito.",
        "El círculo de quintas ordena las tonalidades por la adición de un sostenido.",
        "Una línea de bajo caminante une por grados conjuntos los tiempos del compás.",
        "El timbre de un clarinete en el registro chalumeau es oscuro y pobre en armónicos pares.",
        "La síncopa desplaza el acento al tiempo débil y lo liga al tiempo fuerte siguiente.",
    ],
    "geologia": [
        "Una falla normal hunde el bloque del techo cuando el régimen es extensional.",
        "El granito es una roca ígnea plutónica de cuarzo, feldespato y mica.",
        "La estratigrafía relativa usa la superposición: el estrato de abajo es más antiguo.",
        "Un pliegue anticlinal tiene las rocas más viejas en el núcleo.",
        "La meteorización química del feldespato produce arcillas y libera cationes.",
        "La escala de Mohs ordena minerales por la capacidad de rayar al anterior.",
        "Un tsunami puede generarse por el desplazamiento vertical del fondo oceánico en un sismo.",
        "El metamorfismo de contacto aureola la roca de caja alrededor de un intrusivo.",
        "La datación por uranio-plomo en circón da edades de cristalización ígnea.",
        "Un acuífero confinado está limitado por capas impermeables y puede ser artesiano.",
        "La foliación de un esquisto alinea micas por esfuerzo diferencial.",
        "La dorsal mesoatlántica es un límite divergente donde se crea corteza oceánica.",
        "Un depósito aluvial se acumula donde el río pierde competencia al salir de la montaña.",
        "La lava basáltica de baja viscosidad construye volcanes en escudo.",
        "El karst disuelve caliza y abre dolinas y cuevas por circulación de agua ácida.",
        "Una discordancia angular separa estratos plegados de una cobertura horizontal más joven.",
    ],
    "botanica": [
        "La fotosíntesis en el cloroplasto fija carbono en el ciclo de Calvin.",
        "Un estoma se abre cuando las células oclusivas acumulan potasio y se turgencian.",
        "La xilema conduce agua y sales desde la raíz por tensión-cohesión.",
        "Una flor completa tiene cáliz, corola, androceo y gineceo.",
        "La germinación epigea eleva los cotiledones por encima del suelo.",
        "El floema transporta sacarosa desde las hojas fuente hacia los sumideros.",
        "Una micorriza asocia hifas de hongo con la raíz y amplía la absorción de fósforo.",
        "El meristema apical del tallo mantiene células indiferenciadas que originan los órganos aéreos.",
        "La polinización anemófila produce polen abundante y flores sin néctar.",
        "Un fruto carnoso de tipo baya desarrolla el pericarpio jugoso a partir del ovario.",
        "La dominancia apical inhibe las yemas laterales por auxina producida en el ápice.",
        "Las plantas C4 concentran CO2 en las células de la vaina del haz.",
        "Un anillo de crecimiento en un árbol de clima estacional marca un año de xilema.",
        "La dehiscencia de la antera libera los granos de polen al madurar.",
        "El fototropismo positivo curva el tallo hacia la luz por redistribución de auxina.",
        "Una hoja compuesta pinnada tiene folíolos a lo largo de un raquis.",
    ],
    "arquitectura": [
        "Una viga simplemente apoyada trabaja a flexión con momento máximo en el centro del vano.",
        "El hormigón armado coloca la armadura de tracción donde la sección se fisura.",
        "La transmitancia térmica U de un muro baja cuando aumenta el espesor del aislante.",
        "Un pórtico rígido transmite momento entre viga y columna y resiste cargas laterales.",
        "La escala 1:50 de un plano de obra muestra espesores de muro y carpinterías.",
        "La cimentación por platea reparte la carga del edificio sobre un suelo de baja capacidad.",
        "Un muro cortina cuelga de la estructura y no toma carga gravitatoria del edificio.",
        "La luz natural se modela con el factor de luz diurna en el plano de trabajo.",
        "Una losa alivianada con casetones reduce el peso propio sin perder canto útil.",
        "El detalle de encuentro entre losa y muro evita el puente térmico con una rotura continua.",
        "La circulación vertical de una escalera de dos tramos gira en una meseta intermedia.",
        "Un voladizo exige armadura superior continua y un anclaje en el vano adyacente.",
        "La orientación norte en el hemisferio sur recibe sol bajo en invierno y se protege en verano.",
        "Un entrepiso de acero y chapa colaborante hormigonada actúa como sección mixta.",
        "La junta de dilatación corta la estructura para absorber el movimiento térmico.",
        "La cota de nivel de piso terminado se referencia al cero de la obra.",
    ],
}


def load_dump(root: Path) -> list[dict]:
    proc = subprocess.run(
        ["cargo", "run", "-q", "-p", "sf-bench", "--bin", "suite2_string_dump"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout or f"suite2_string_dump exited {proc.returncode}")
    records = []
    for line in proc.stdout.splitlines():
        if line.strip():
            records.append(json.loads(line))
    if not records:
        raise SystemExit("suite2_string_dump printed no JSON lines")
    return records


def assert_seeds_match(records: list[dict]) -> None:
    by_domain: dict[str, list[str]] = {}
    order: list[str] = []
    for rec in records:
        if rec.get("kind") != "seed":
            continue
        domain = rec["domain"]
        if domain not in by_domain:
            order.append(domain)
            by_domain[domain] = []
        by_domain[domain].append(rec["text"])
    if order != CANONICAL_DOMAINS:
        raise SystemExit(f"seed domain order {order} != {CANONICAL_DOMAINS}")
    for domain in CANONICAL_DOMAINS:
        got = by_domain.get(domain)
        expected = CANONICAL_SEED_SENTENCES[domain]
        if got != expected:
            raise SystemExit(f"seed mismatch for domain {domain}")


def unique_texts(records: list[dict]) -> list[str]:
    texts: list[str] = []
    seen: set[str] = set()
    for rec in records:
        text = rec["text"]
        if text not in seen:
            seen.add(text)
            texts.append(text)
    return texts


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    print("=" * 75)
    print("3HM Suite 2 Generator: BAAI/bge-m3 binary32")
    print("=" * 75)
    records = load_dump(root)
    assert_seeds_match(records)
    texts = unique_texts(records)
    if not texts:
        raise SystemExit("no strings to embed")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[*] Initializing BAAI/bge-m3 on {device} (strict IEEE 754 binary32)...")
    model = SentenceTransformer("BAAI/bge-m3", device=device)
    model = model.to(dtype=torch.float32)
    vectors = model.encode(texts, batch_size=32, normalize_embeddings=True)
    vectors = np.ascontiguousarray(vectors, dtype="<f4")
    if vectors.shape != (len(texts), DIM):
        raise SystemExit(f"expected shape {(len(texts), DIM)}, got {vectors.shape}")
    print(f"[*] Encoded {len(texts)} unique strings on {device}.")

    fixtures = root / "crates" / "sf-bench" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    bin_path = fixtures / "oos_bge_m3_vectors.bin"
    meta_path = fixtures / "oos_bge_m3_metadata.json"
    bin_path.write_bytes(vectors.tobytes())
    manifest = {
        "model": "BAAI/bge-m3",
        "precision": "IEEE 754 binary32",
        "device": device,
        "vector_dim": DIM,
        "strings": texts,
    }
    meta_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[*] Wrote {bin_path} ({bin_path.stat().st_size} bytes)")
    print(f"[*] Wrote {meta_path} ({meta_path.stat().st_size} bytes)")
    print("=" * 75)


if __name__ == "__main__":
    main()
