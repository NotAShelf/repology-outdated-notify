{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = (with pkgs; [
    python3Full
  ]) ++ (with pkgs.python3Packages; [
    # Tools
    black
    mypy

    # Dependencies
    feedparser
    requests
  ]);
}
