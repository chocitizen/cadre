import type { AiGenerateRequest, AiGenerateResult, AiProvider } from "../contracts";

export interface TestAiProviderOptions {
  readonly environment?: NodeJS.ProcessEnv;
  readonly responseText?: string;
}

export class TestAiProvider implements AiProvider {
  readonly id = "test";
  readonly defaultModel = "cadre-test-v0.1";
  readonly #enabled: boolean;
  readonly #responseText: string;

  constructor(options: TestAiProviderOptions = {}) {
    const environment = options.environment ?? process.env;
    this.#enabled =
      environment.CADRE_ENABLE_TEST_PROVIDER === "true" &&
      (environment.NODE_ENV === "test" || environment.NODE_ENV === "development");
    this.#responseText = options.responseText ?? "CADRE test response.";

    if (!this.#enabled) {
      throw new Error(
        "The test AI provider requires CADRE_ENABLE_TEST_PROVIDER=true outside production."
      );
    }
  }

  async generate(request: AiGenerateRequest): Promise<AiGenerateResult> {
    if (!this.#enabled) {
      throw new Error("The test AI provider is disabled.");
    }

    return {
      providerId: this.id,
      model: request.model?.trim() || this.defaultModel,
      externalResponseId: null,
      text: this.#responseText,
      usage: null
    };
  }
}
