declare module 'turndown' {
  export interface TurndownOptions {
    headingStyle?: 'setext' | 'atx';
    codeBlockStyle?: 'fenced' | 'indented';
    bulletListMarker?: '-' | '*' | '+';
    emDelimiter?: '_' | '*';
    strongDelimiter?: '**' | '__';
    linkStyle?: 'inlined' | 'referenced';
    linkReferenceStyle?: 'full' | 'collapsed' | 'shortcut';
    quoteMarker?: '"' | "'";
    breakReturn?: boolean;
    preserveComments?: boolean;
  }

  export interface Rule {
    readonly name: string;
    readonly nodeTypes: string | string[];
    readonly handler: (node: any, options: any) => string;
  }

  export class TurndownService {
    constructor(options?: TurndownOptions);
    use(plugin: (service: TurndownService) => void): void;
    addRule(name: string, rule: Partial<Rule>): void;
    turndown(html: string): string;
  }

  export default TurndownService;
}