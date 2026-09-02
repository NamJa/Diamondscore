#!/usr/bin/env bash
# SofaScore API를 OkHttp로 호출해 본문을 stdout에 출력한다.
# curl/Python/Node/JDK HttpClient는 TLS 핑거프린트로 403이 나므로(계획서 §13 A-3) OkHttp를 쓴다.
# 사용: sofa-fetch.sh <URL> > out.json      (JDK 17+ 필요)
set -euo pipefail
URL="${1:?usage: sofa-fetch.sh <URL>}"
DIR="${HOME}/.cache/diamondscore-tools"; mkdir -p "$DIR"
M=https://repo1.maven.org/maven2
for j in com/squareup/okhttp3/okhttp/4.12.0/okhttp-4.12.0.jar \
         com/squareup/okio/okio-jvm/3.9.0/okio-jvm-3.9.0.jar \
         org/jetbrains/kotlin/kotlin-stdlib/1.9.24/kotlin-stdlib-1.9.24.jar; do
  f="$DIR/$(basename "$j")"; [ -s "$f" ] || curl -fsSL "$M/$j" -o "$f"
done
CP="$DIR/okhttp-4.12.0.jar:$DIR/okio-jvm-3.9.0.jar:$DIR/kotlin-stdlib-1.9.24.jar"
[ -s "$DIR/Fetch.java" ] || cat > "$DIR/Fetch.java" <<'JAVA'
import okhttp3.*;
public class Fetch {
  public static void main(String[] a) throws Exception {
    Request req = new Request.Builder().url(a[0]).header("User-Agent", "DiamondScore-spike/0.1").build();
    try (Response r = new OkHttpClient().newCall(req).execute()) {
      String body = r.body().string();
      if (r.code() != 200) { System.err.println("HTTP " + r.code() + " " + body); System.exit(1); }
      System.out.print(body);
    }
  }
}
JAVA
exec java -cp "$CP" "$DIR/Fetch.java" "$URL"
