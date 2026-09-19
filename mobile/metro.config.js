// Les textes de l'app viennent de ../app/locales/*.json : une seule source
// pour le web, le bot et le mobile. Metro ne regarde que le dossier du projet
// par défaut, on lui ajoute donc celui des traductions.
const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
config.watchFolders = [...(config.watchFolders || []), path.resolve(__dirname, "..", "app", "locales")];

module.exports = config;
