/**
 * C++ HTTP Service Example
 * Production-ready template with health checks and JSON support
 */
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <iostream>
#include <cstdlib>

using json = nlohmann::json;

// Get port from environment variable
int get_port() {
    const char* port_str = std::getenv("PORT");
    return port_str ? std::atoi(port_str) : 8080;
}

int main() {
    httplib::Server svr;
    const int port = get_port();

    // Root endpoint
    svr.Get("/", [](const httplib::Request&, httplib::Response& res) {
        json response = {
            {"message", "C++ HTTP Service"},
            {"version", "1.0.0"},
            {"endpoints", {
                "/health",
                "/api/echo"
            }}
        };
        res.set_content(response.dump(), "application/json");
    });

    // Health check endpoint (required for Railway/Cloud Run)
    svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        json response = {
            {"status", "healthy"},
            {"timestamp", std::time(nullptr)}
        };
        res.set_content(response.dump(), "application/json");
    });

    // Echo endpoint (example POST)
    svr.Post("/api/echo", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto request_json = json::parse(req.body);
            json response = {
                {"echo", request_json["message"]},
                {"length", request_json["message"].get<std::string>().length()}
            };
            res.set_content(response.dump(), "application/json");
        } catch (const std::exception& e) {
            json error = {
                {"error", "Invalid JSON"},
                {"message", e.what()}
            };
            res.status = 400;
            res.set_content(error.dump(), "application/json");
        }
    });

    // Start server
    std::cout << "Starting C++ HTTP server on port " << port << std::endl;
    std::cout << "Health check: http://localhost:" << port << "/health" << std::endl;
    
    if (!svr.listen("0.0.0.0", port)) {
        std::cerr << "Failed to start server" << std::endl;
        return 1;
    }

    return 0;
}
