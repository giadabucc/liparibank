package com.lipari.bank.web;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;
import com.lipari.bank.security.JwtService;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final JdbcTemplate jdbc;
    private final PasswordEncoder encoder;
    private final JwtService jwtService;

    @PostMapping("/login")
    public ResponseEntity<Map<String, String>> login(@RequestBody Map<String, String> body) {
        String username = body.get("username");
        String password = body.get("password");

        String hash = jdbc.queryForObject(
                "SELECT password_hash FROM app_user WHERE username = ?",
                String.class, username);

        if (hash == null || !encoder.matches(password, hash)) {
            return ResponseEntity.status(401).body(Map.of("error", "invalid credentials"));
        }
        return ResponseEntity.ok(Map.of("token", jwtService.generate(username)));
    }
}
