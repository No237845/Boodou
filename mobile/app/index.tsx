import { Redirect } from "expo-router";
import React from "react";

import { useI18n } from "@/i18n";
import { Loading } from "@/ui";

/** Premier lancement : choix de la langue. Ensuite : accueil. */
export default function Index() {
  const { lang, ready } = useI18n();
  if (!ready) return <Loading />;
  return <Redirect href={lang ? "/home" : "/lang"} />;
}
