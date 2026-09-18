package com.lipari.bank.security;

import java.util.Date;
import javax.crypto.SecretKey;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

@Service
public class JwtService {

    /**
     * ANTI-PATTERN A (intenzionale): JWT secret hardcoded nel codice sorgente.
     * Chiunque legga il repo (developer interni, GitHub leak, container image dump)
     * può firmare token validi e impersonare qualsiasi utente.
     *
     * Pattern enterprise corretto: leggere il secret da application.yml con valore
     * iniettato da env var (${JWT_SECRET}), a sua volta caricato da K8s Secret /
     * AWS Secrets Manager / HashiCorp Vault. Mai in chiaro nel sorgente.
     *
     * Il subagent `security-reviewer` del Bootcamp Claude Code deve trovarlo.
     */
    private static final String SECRET = "demo-jwt-secret-for-bootcamp-banking-system-must-be-long-enough";

    private static final long EXPIRATION_MS = 3_600_000L;   // 1 ora

    private SecretKey signingKey() {
        return Keys.hmacShaKeyFor(SECRET.getBytes());
    }

    public String generate(String username) {
        return Jwts.builder()
                .subject(username)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + EXPIRATION_MS))
                .signWith(signingKey())
                .compact();
    }

    public String parseUsername(String token) {
        return Jwts.parser()
                .verifyWith(signingKey())
                .build()
                .parseSignedClaims(token)
                .getPayload()
                .getSubject();
    }
}
