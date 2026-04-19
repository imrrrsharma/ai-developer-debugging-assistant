"""
Classifies log type and detects well-known error patterns for quick-fix suggestions.
"""
import re
from dataclasses import dataclass
from typing import List, Optional
from backend.schemas import QuickFix


LOG_TYPES = {
    "java_spring": "Java Spring Boot",
    "java_generic": "Java Generic",
    "nodejs": "Node.js",
    "python": "Python",
    "generic": "Generic",
}

# (pattern, log_type, weight)
_TYPE_SIGNALS = [
    (re.compile(r"\bSpringApplication\b|\bspring\.boot\b|\bDispatcherServlet\b", re.I), "java_spring", 3),
    (re.compile(r"^\s+at [\w.$]+\([\w.]+\.java:\d+\)", re.M), "java_generic", 2),
    (re.compile(r"at Object\.<anonymous>|at Module\._compile|\.js:\d+:\d+"), "nodejs", 3),
    (re.compile(r"Traceback \(most recent call last\)|\.py\", line \d+"), "python", 3),
    (re.compile(r"\bERROR\b|\bWARN\b|\bFATAL\b"), "generic", 1),
]

# Well-known error fingerprints → (label, action, optional_command)
_KNOWN_ERRORS = [
    {
        "pattern": re.compile(r"NullPointerException", re.I),
        "error_type": "NullPointerException",
        "quick_fixes": [
            QuickFix(label="Add null check", action="Wrap the offending call with a null check or use Optional<T>"),
            QuickFix(label="Enable NPE details (Java 14+)", action="Add JVM flag: -XX:+ShowCodeDetailsInExceptionMessages",
                     command="-XX:+ShowCodeDetailsInExceptionMessages"),
        ],
    },
    {
        "pattern": re.compile(r"OutOfMemoryError|java\.lang\.OutOfMemoryError", re.I),
        "error_type": "OutOfMemoryError",
        "quick_fixes": [
            QuickFix(label="Increase heap size", action="Increase JVM heap: -Xmx4g -Xms1g",
                     command="-Xmx4g -Xms1g"),
            QuickFix(label="Enable GC logging", action="Add: -Xlog:gc* to diagnose memory pressure",
                     command="-Xlog:gc*"),
            QuickFix(label="Take heap dump", action="Add: -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heapdump.hprof",
                     command="-XX:+HeapDumpOnOutOfMemoryError"),
        ],
    },
    {
        "pattern": re.compile(r"TimeoutException|Kafka.*timeout|org\.apache\.kafka.*TimeoutException", re.I),
        "error_type": "KafkaTimeoutError",
        "quick_fixes": [
            QuickFix(label="Increase request.timeout.ms", action="Set request.timeout.ms=60000 in producer/consumer config",
                     command="request.timeout.ms=60000"),
            QuickFix(label="Check Kafka broker health", action="Run: kafka-topics.sh --bootstrap-server localhost:9092 --list",
                     command="kafka-topics.sh --bootstrap-server localhost:9092 --list"),
            QuickFix(label="Verify network path", action="Ensure brokers are reachable from this host on port 9092"),
        ],
    },
    {
        "pattern": re.compile(r"(Connection refused|could not connect|Unable to acquire JDBC|HikariPool.*connection|FATAL.*database)", re.I),
        "error_type": "DatabaseConnectionError",
        "quick_fixes": [
            QuickFix(label="Check DB config", action="Verify spring.datasource.url, username, password in application.properties"),
            QuickFix(label="Test connectivity", action="Run: psql -h <host> -U <user> -d <db> or equivalent CLI ping",
                     command="psql -h localhost -U postgres -d mydb -c '\\conninfo'"),
            QuickFix(label="Check DB is running", action="Run: systemctl status postgresql  or  docker ps | grep postgres",
                     command="systemctl status postgresql"),
        ],
    },
    {
        "pattern": re.compile(r"StackOverflowError", re.I),
        "error_type": "StackOverflowError",
        "quick_fixes": [
            QuickFix(label="Find recursive call", action="Check for unbounded recursion or circular bean dependencies"),
            QuickFix(label="Increase thread stack", action="Add JVM flag: -Xss4m",
                     command="-Xss4m"),
        ],
    },
    {
        "pattern": re.compile(r"ClassNotFoundException|NoClassDefFoundError", re.I),
        "error_type": "ClassNotFoundError",
        "quick_fixes": [
            QuickFix(label="Check classpath / dependencies", action="Verify the class is present in pom.xml/build.gradle and the fat-jar is correctly built"),
            QuickFix(label="Rebuild artifact", action="Run: mvn clean package -DskipTests  or  gradle clean build",
                     command="mvn clean package -DskipTests"),
        ],
    },
    {
        "pattern": re.compile(r"ModuleNotFoundError|ImportError|No module named", re.I),
        "error_type": "PythonImportError",
        "quick_fixes": [
            QuickFix(label="Install missing package", action="Run: pip install <package-name>  or check requirements.txt",
                     command="pip install -r requirements.txt"),
            QuickFix(label="Check virtual environment", action="Ensure the correct venv is activated: source .venv/bin/activate"),
        ],
    },
    {
        "pattern": re.compile(r"ECONNREFUSED|ENOTFOUND|socket hang up|getaddrinfo ENOTFOUND", re.I),
        "error_type": "NodeNetworkError",
        "quick_fixes": [
            QuickFix(label="Check target service URL", action="Verify the host/port in your environment config is reachable"),
            QuickFix(label="Test with curl", action="Run: curl -v http://<host>:<port>/health",
                     command="curl -v http://localhost:3000/health"),
        ],
    },
    {
        "pattern": re.compile(r"ConcurrentModificationException", re.I),
        "error_type": "ConcurrentModificationException",
        "quick_fixes": [
            QuickFix(label="Use CopyOnWriteArrayList or synchronized block", action="Replace ArrayList with CopyOnWriteArrayList or synchronize iteration"),
            QuickFix(label="Use Iterator.remove()", action="Avoid modifying a collection while iterating it with for-each; use iterator.remove() instead"),
        ],
    },
]


@dataclass
class ClassificationResult:
    log_type: str                   # key from LOG_TYPES
    log_type_label: str             # human-readable
    detected_error_type: Optional[str]
    quick_fixes: List[QuickFix]


def classify(text: str) -> ClassificationResult:
    log_type = _detect_log_type(text)
    error_type, quick_fixes = _detect_known_error(text)

    return ClassificationResult(
        log_type=log_type,
        log_type_label=LOG_TYPES.get(log_type, "Generic"),
        detected_error_type=error_type,
        quick_fixes=quick_fixes,
    )


def _detect_log_type(text: str) -> str:
    scores: dict = {}
    for pattern, log_type, weight in _TYPE_SIGNALS:
        if pattern.search(text):
            scores[log_type] = scores.get(log_type, 0) + weight

    if not scores:
        return "generic"

    best = max(scores, key=lambda k: scores[k])
    # java_spring beats java_generic
    if "java_spring" in scores and "java_generic" in scores:
        return "java_spring"
    return best


def _detect_known_error(text: str):
    for entry in _KNOWN_ERRORS:
        if entry["pattern"].search(text):
            return entry["error_type"], entry["quick_fixes"]
    return None, []
