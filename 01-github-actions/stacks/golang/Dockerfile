# ==========================================
# Production Multi-Stage Go (Golang) Dockerfile
# ==========================================
# Stage 1: Build Static Binary
FROM golang:1.22-alpine AS builder
WORKDIR /src

RUN apk add --no-cache ca-certificates git

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . .

# Compile static binary: CGO_ENABLED=0 removes glibc dependency
# -ldflags="-w -s" strips debug symbols and DWARF tables to minimize binary size
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s -extldflags '-static'" \
    -o /bin/server ./cmd/server

# Stage 2: Pure Scratch Container (Zero OS, Zero Shell, ~15MB Image)
FROM scratch

# Import CA certificates for TLS/HTTPS outbound calls
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
# Import the statically compiled binary
COPY --from=builder /bin/server /server

USER 10001:10001
EXPOSE 8080

ENTRYPOINT ["/server"]
