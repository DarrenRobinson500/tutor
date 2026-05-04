declare module "monaco-yaml" {
  import * as monaco from "monaco-editor";

  export function configureMonacoYaml(
    monacoInstance: typeof monaco,
    options: any
  ): void;
}
