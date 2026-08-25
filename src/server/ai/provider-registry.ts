import type { AiProvider } from "./contracts";
import { OpenAiProvider } from "./providers/openai";
import { TestAiProvider } from "./providers/test";

export interface AiProviderRegistryOptions {
  readonly providers: readonly AiProvider[];
  readonly defaultProviderId: string;
}

export class AiProviderRegistry {
  readonly #providers = new Map<string, AiProvider>();
  readonly #defaultProviderId: string;

  constructor(options: AiProviderRegistryOptions) {
    for (const provider of options.providers) {
      if (this.#providers.has(provider.id)) {
        throw new Error(`Duplicate AI provider registration: ${provider.id}`);
      }

      this.#providers.set(provider.id, provider);
    }

    if (!this.#providers.has(options.defaultProviderId)) {
      throw new Error(`Default AI provider is not registered: ${options.defaultProviderId}`);
    }

    this.#defaultProviderId = options.defaultProviderId;
  }

  resolve(providerId = this.#defaultProviderId): AiProvider {
    const provider = this.#providers.get(providerId);

    if (!provider) {
      throw new Error(`AI provider is not registered: ${providerId}`);
    }

    return provider;
  }

  list(): readonly Pick<AiProvider, "id" | "defaultModel">[] {
    return Array.from(this.#providers.values(), ({ id, defaultModel }) => ({
      id,
      defaultModel
    }));
  }
}

export function createProviderRegistry(
  environment: NodeJS.ProcessEnv = process.env
): AiProviderRegistry {
  const providers: AiProvider[] = [
    new OpenAiProvider({
      apiKey: environment.OPENAI_API_KEY,
      model: environment.OPENAI_MODEL
    })
  ];

  if (
    environment.CADRE_ENABLE_TEST_PROVIDER === "true" &&
    (environment.NODE_ENV === "test" || environment.NODE_ENV === "development")
  ) {
    providers.push(new TestAiProvider({ environment }));
  }

  return new AiProviderRegistry({
    providers,
    defaultProviderId:
      environment.AI_PROVIDER?.trim() || environment.CADRE_AI_PROVIDER?.trim() || "openai"
  });
}
