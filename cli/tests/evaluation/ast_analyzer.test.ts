import { describe, it, expect } from "vitest";
import { analyzeCode, extractCodeBlock } from "../../../evaluation/ast_analyzer";

describe("ast_analyzer (Deterministic TypeScript Compiler API Evaluator)", () => {
  it("extracts code blocks from markdown fences", () => {
    const markdown = "Here is the refactored code:\n```typescript\nconst a = 1;\n```\nDone.";
    const code = extractCodeBlock(markdown);
    expect(code).toBe("const a = 1;");
  });

  it("penalizes prohibited framework and ORM imports", () => {
    const spaghettiCode = `
      import express from 'express';
      import { Entity, Column } from 'typeorm';
      import axios from 'axios';

      export class OrderService {
        async getOrders() {
          return axios.get('/api');
        }
      }
    `;
    const metrics = analyzeCode(spaghettiCode);
    expect(metrics.prohibitedImports).toEqual(expect.arrayContaining(["express", "typeorm", "axios"]));
    expect(metrics.domainBoundaryScore).toBe(0);
  });

  it("awards maximum domain boundary score when zero prohibited imports exist", () => {
    const cleanCode = `
      export class Order {
        constructor(public readonly id: string) {}
      }
    `;
    const metrics = analyzeCode(cleanCode);
    expect(metrics.domainBoundaryScore).toBe(30.0);
    expect(metrics.prohibitedImports).toHaveLength(0);
  });

  it("detects constructor guard clauses and throw statements", () => {
    const guardedCode = `
      export class Email {
        constructor(private readonly value: string) {
          if (!value.includes('@')) {
            throw new Error('Invalid email');
          }
        }
      }
    `;
    const metrics = analyzeCode(guardedCode);
    expect(metrics.hasConstructorGuards).toBe(true);
    expect(metrics.invariantScore).toBeGreaterThanOrEqual(15.0);
  });

  it("counts exact AnyKeyword tokens without false positives on strings or comments", () => {
    const trickyCode = `
      // This is a comment about any kind of design pattern
      const message = "Do not use any in code";
      const actualAny: any = 123;
      const secondAny: any = "test";
    `;
    const metrics = analyzeCode(trickyCode);
    // There are exactly 2 AnyKeyword tokens in the AST
    expect(metrics.anyOccurrences).toBe(2);
    // 20 - (2 * 5) = 10
    expect(metrics.typingScore).toBe(10.0);
  });

  it("identifies port interfaces and contract declarations", () => {
    const portsCode = `
      export interface IOrderRepository {
        save(order: unknown): Promise<void>;
      }
      export type OrderId = string;
    `;
    const metrics = analyzeCode(portsCode);
    expect(metrics.declaredContracts).toContain("IOrderRepository");
    expect(metrics.declaredContracts).toContain("OrderId");
    expect(metrics.portsScore).toBe(20.0);
  });

  it("evaluates a canonical Clean Architecture unit with high CAS composite score (>= 85)", () => {
    const canonicalCode = `
      export interface IUserRepository {
        findById(id: string): Promise<User | null>;
      }

      export class User {
        constructor(public readonly id: string, public readonly name: string) {
          if (!name || name.trim().length === 0) {
            throw new Error('Name cannot be empty');
          }
        }
      }

      export type UserResult = { success: true; user: User } | { success: false; error: string };
    `;
    const metrics = analyzeCode(canonicalCode);
    expect(metrics.domainBoundaryScore).toBe(30.0);
    expect(metrics.typingScore).toBe(20.0);
    expect(metrics.compositeScore).toBeGreaterThanOrEqual(85.0);
  });
});
