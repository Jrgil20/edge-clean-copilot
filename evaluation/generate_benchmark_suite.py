#!/usr/bin/env python3
"""
Generates the 30-case Legacy Benchmark Suite for Edge Clean Copilot.
Creates synthetic paired ChatML test cases covering 5 key architectural categories:
  A. ORM & Database Direct Coupling (7 cases)
  B. HTTP, Network & Third-Party SDK Leakage (7 cases)
  C. Primitive Obsession, Missing Invariants & Untyped Throws (8 cases)
  D. TypeScript Any-Type Proliferation & Lack of Contracts (5 cases)
  E. Monolithic God Classes & Multi-Antipattern Controllers (3 cases)
"""

import json
from pathlib import Path

OUTPUT_FILE = Path(__file__).resolve().parent / "legacy_benchmark_suite.jsonl"

CASES = [
    # --------------------------------------------------------------------------
    # CATEGORY A: ORM & DATABASE DIRECT COUPLING (7 cases)
    # --------------------------------------------------------------------------
    {
        "label": "Case 01: Direct Prisma Client Coupling in Domain Entity",
        "category": "ORM_DIRECT_COUPLING",
        "legacy": """import { PrismaClient } from '@prisma/client';

export class UserAccount {
  private prisma = new PrismaClient();

  constructor(public id: string, public email: string) {}

  async updateEmail(newEmail: string): Promise<void> {
    this.email = newEmail;
    await this.prisma.user.update({
      where: { id: this.id },
      data: { email: newEmail }
    });
  }
}""",
        "canonical": """// 1. Domain Layer: Pure entity with zero external dependencies
export class UserAccount {
  private constructor(
    public readonly id: string,
    public readonly email: string
  ) {}

  public static create(id: string, email: string): UserAccount {
    return new UserAccount(id, email);
  }

  public changeEmail(newEmail: string): UserAccount {
    return new UserAccount(this.id, newEmail);
  }
}

// 2. Application Layer: Port Interface
export interface IUserAccountRepository {
  findById(id: string): Promise<UserAccount | null>;
  save(account: UserAccount): Promise<void>;
}

// 3. Application Layer: Use Case with Result pattern
export class UpdateUserEmailUseCase {
  constructor(private readonly userRepo: IUserAccountRepository) {}

  async execute(id: string, newEmail: string): Promise<boolean> {
    const user = await this.userRepo.findById(id);
    if (!user) return false;
    const updated = user.changeEmail(newEmail);
    await this.userRepo.save(updated);
    return true;
  }
}"""
    },
    {
        "label": "Case 02: TypeORM ActiveRecord Entity Coupling",
        "category": "ORM_DIRECT_COUPLING",
        "legacy": """import { Entity, PrimaryGeneratedColumn, Column, BaseEntity } from 'typeorm';

@Entity('products')
export class Product extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column('decimal')
  price: number;

  async applyDiscount(percent: number): Promise<void> {
    this.price = this.price * (1 - percent / 100);
    await this.save();
  }
}""",
        "canonical": """// 1. Domain Layer: Pure Product entity
export class Product {
  private constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly price: number
  ) {}

  public static create(id: string, name: string, price: number): Product {
    if (price < 0) throw new Error('Price cannot be negative');
    return new Product(id, name, price);
  }

  public applyDiscount(percent: number): Product {
    const discounted = this.price * (1 - percent / 100);
    return new Product(this.id, this.name, Math.max(0, discounted));
  }
}

// 2. Application Layer: Repository Port
export interface IProductRepository {
  findById(id: string): Promise<Product | null>;
  save(product: Product): Promise<void>;
}"""
    },
    {
        "label": "Case 03: Raw PostgreSQL Client in Domain Logic",
        "category": "ORM_DIRECT_COUPLING",
        "legacy": """import { Client } from 'pg';

export class InventoryService {
  private client = new Client();

  async deductStock(productId: string, quantity: number): Promise<void> {
    await this.client.connect();
    const res = await this.client.query('SELECT stock FROM inventory WHERE product_id = $1', [productId]);
    const currentStock = res.rows[0].stock;
    if (currentStock < quantity) throw new Error('Out of stock');
    await this.client.query('UPDATE inventory SET stock = stock - $1 WHERE product_id = $2', [quantity, productId]);
  }
}""",
        "canonical": """// 1. Domain Layer: Pure Inventory Item
export class InventoryItem {
  constructor(public readonly productId: string, public readonly stock: number) {}

  public deduct(quantity: number): InventoryItem {
    if (quantity <= 0) throw new Error('Deduction quantity must be positive');
    if (this.stock < quantity) throw new Error('Insufficient stock');
    return new InventoryItem(this.productId, this.stock - quantity);
  }
}

// 2. Application Layer: Inventory Port
export interface IInventoryRepository {
  findByProductId(productId: string): Promise<InventoryItem | null>;
  save(item: InventoryItem): Promise<void>;
}

// 3. Application Layer: Deduct Stock Use Case
export class DeductStockUseCase {
  constructor(private readonly repo: IInventoryRepository) {}

  async execute(productId: string, qty: number): Promise<void> {
    const item = await this.repo.findByProductId(productId);
    if (!item) throw new Error('Item not found');
    const updated = item.deduct(qty);
    await this.repo.save(updated);
  }
}"""
    },
    {
        "label": "Case 04: Mongoose Model Direct Usage in Domain",
        "category": "ORM_DIRECT_COUPLING",
        "legacy": """import mongoose, { Schema } from 'mongoose';

const SubscriptionSchema = new Schema({
  userId: String,
  status: String,
  expiresAt: Date
});

export const SubscriptionModel = mongoose.model('Subscription', SubscriptionSchema);

export async function renewSubscription(userId: string): Promise<void> {
  const sub = await SubscriptionModel.findOne({ userId });
  if (!sub) throw new Error('Subscription not found');
  sub.status = 'ACTIVE';
  sub.expiresAt = new Date(Date.now() + 30 * 24 * 3600 * 1000);
  await sub.save();
}""",
        "canonical": """// 1. Domain Layer: Pure Subscription Entity
export class Subscription {
  constructor(
    public readonly userId: string,
    public readonly status: 'ACTIVE' | 'EXPIRED',
    public readonly expiresAt: Date
  ) {}

  public renew(durationDays: number): Subscription {
    const newExpiry = new Date(Date.now() + durationDays * 86400000);
    return new Subscription(this.userId, 'ACTIVE', newExpiry);
  }
}

// 2. Application Layer: Port Interface
export interface ISubscriptionRepository {
  findByUserId(userId: string): Promise<Subscription | null>;
  save(subscription: Subscription): Promise<void>;
}

// 3. Application Layer: Renew Subscription Use Case
export class RenewSubscriptionUseCase {
  constructor(private readonly repo: ISubscriptionRepository) {}

  async execute(userId: string): Promise<Subscription> {
    const sub = await this.repo.findByUserId(userId);
    if (!sub) throw new Error('Subscription not found');
    const renewed = sub.renew(30);
    await this.repo.save(renewed);
    return renewed;
  }
}"""
    },
    {
        "label": "Case 05: SQLite Direct Query in Order Processing",
        "category": "ORM_DIRECT_COUPLING",
        "legacy": """import sqlite3 from 'sqlite3';

export class OrderService {
  private db = new sqlite3.Database(':memory:');

  createOrder(customerId: string, amount: number): void {
    this.db.run('INSERT INTO orders (customer_id, amount) VALUES (?, ?)', [customerId, amount]);
  }
}""",
        "canonical": """// 1. Domain Layer: Pure Order Entity
export class Order {
  constructor(
    public readonly id: string,
    public readonly customerId: string,
    public readonly amount: number
  ) {
    if (amount <= 0) throw new Error('Order amount must be positive');
  }
}

// 2. Application Layer: Port
export interface IOrderRepository {
  save(order: Order): Promise<void>;
}

// 3. Application Layer: Create Order Use Case
export class CreateOrderUseCase {
  constructor(private readonly orderRepo: IOrderRepository) {}

  async execute(id: string, customerId: string, amount: number): Promise<Order> {
    const order = new Order(id, customerId, amount);
    await this.orderRepo.save(order);
    return order;
  }
}"""
    },
    {
        "label": "Case 06: Knex Query Builder in Domain Logic",
        "category": "ORM_DIRECT_COUPLING",
        "legacy": """import knex from 'knex';

const db = knex({ client: 'pg' });

export class CustomerBalance {
  async credit(customerId: string, amount: number): Promise<void> {
    await db('customers').where('id', customerId).increment('balance', amount);
  }
}""",
        "canonical": """// 1. Domain Layer: Pure Customer Entity
export class Customer {
  constructor(public readonly id: string, public readonly balance: number) {}

  public credit(amount: number): Customer {
    if (amount <= 0) throw new Error('Credit amount must be positive');
    return new Customer(this.id, this.balance + amount);
  }
}

// 2. Application Layer: Repository Port
export interface ICustomerRepository {
  findById(id: string): Promise<Customer | null>;
  save(customer: Customer): Promise<void>;
}

// 3. Application Layer: Credit Customer Use Case
export class CreditCustomerUseCase {
  constructor(private readonly repo: ICustomerRepository) {}

  async execute(customerId: string, amount: number): Promise<Customer> {
    const customer = await this.repo.findById(customerId);
    if (!customer) throw new Error('Customer not found');
    const updated = customer.credit(amount);
    await this.repo.save(updated);
    return updated;
  }
}"""
    },
    {
        "label": "Case 07: Sequelize Model Inheritance in Domain",
        "category": "ORM_DIRECT_COUPLING",
        "legacy": """import { Model, DataTypes } from 'sequelize';

export class Invoice extends Model {
  public id!: number;
  public total!: number;

  public markAsPaid(): void {
    this.setDataValue('paid', true);
    this.save();
  }
}""",
        "canonical": """// 1. Domain Layer: Pure Invoice Entity
export class Invoice {
  constructor(
    public readonly id: string,
    public readonly total: number,
    public readonly isPaid: boolean = false
  ) {}

  public markAsPaid(): Invoice {
    return new Invoice(this.id, this.total, true);
  }
}

// 2. Application Layer: Repository Port
export interface IInvoiceRepository {
  findById(id: string): Promise<Invoice | null>;
  save(invoice: Invoice): Promise<void>;
}"""
    },

    # --------------------------------------------------------------------------
    # CATEGORY B: HTTP, NETWORK & THIRD-PARTY SDK LEAKAGE (7 cases)
    # --------------------------------------------------------------------------
    {
        "label": "Case 08: Direct Axios HTTP Client in Domain Entity",
        "category": "HTTP_NETWORK_LEAKAGE",
        "legacy": """import axios from 'axios';

export class PaymentProcessor {
  async chargeCreditCard(token: string, amount: number): Promise<boolean> {
    const res = await axios.post('https://api.paymentgateway.com/charges', { token, amount });
    return res.data.success;
  }
}""",
        "canonical": """// 1. Application Layer: Abstract Payment Gateway Port
export interface IPaymentGatewayPort {
  charge(token: string, amount: number): Promise<boolean>;
}

// 2. Application Layer: Charge Card Use Case
export class ChargeCardUseCase {
  constructor(private readonly paymentGateway: IPaymentGatewayPort) {}

  async execute(token: string, amount: number): Promise<boolean> {
    if (amount <= 0) throw new Error('Amount must be positive');
    return this.paymentGateway.charge(token, amount);
  }
}"""
    },
    {
        "label": "Case 09: Direct Global Fetch in Domain Logic",
        "category": "HTTP_NETWORK_LEAKAGE",
        "legacy": """export class GeolocationService {
  async getCountryByIp(ip: string): Promise<string> {
    const res = await fetch(`https://ipapi.co/${ip}/json/`);
    const data = await res.json();
    return data.country_name;
  }
}""",
        "canonical": """// 1. Application Layer: Geolocation Port Interface
export interface IGeolocationPort {
  lookupCountry(ip: string): Promise<string>;
}

// 2. Application Layer: Lookup Country Use Case
export class LookupCountryUseCase {
  constructor(private readonly geoPort: IGeolocationPort) {}

  async execute(ip: string): Promise<string> {
    return this.geoPort.lookupCountry(ip);
  }
}"""
    },
    {
        "label": "Case 10: Direct SendGrid SDK Coupling",
        "category": "HTTP_NETWORK_LEAKAGE",
        "legacy": """import sendgrid from '@sendgrid/mail';

export class WelcomeNotification {
  async sendWelcomeEmail(userEmail: string): Promise<void> {
    sendgrid.setApiKey('SG.sample_key');
    await sendgrid.send({
      to: userEmail,
      from: 'noreply@domain.com',
      subject: 'Welcome',
      text: 'Welcome to our platform'
    });
  }
}""",
        "canonical": """// 1. Application Layer: Notification Port Interface
export interface IEmailNotificationPort {
  send(recipient: string, subject: string, body: string): Promise<void>;
}

// 2. Application Layer: Send Welcome Email Use Case
export class SendWelcomeEmailUseCase {
  constructor(private readonly emailPort: IEmailNotificationPort) {}

  async execute(userEmail: string): Promise<void> {
    await this.emailPort.send(userEmail, 'Welcome', 'Welcome to our platform');
  }
}"""
    },
    {
        "label": "Case 11: Direct Redis Client Coupling in Cache",
        "category": "HTTP_NETWORK_LEAKAGE",
        "legacy": """import Redis from 'ioredis';

export class SessionCache {
  private redis = new Redis();

  async storeSession(sessionId: string, userId: string): Promise<void> {
    await this.redis.set(`session:${sessionId}`, userId, 'EX', 3600);
  }
}""",
        "canonical": """// 1. Application Layer: Cache Port Contract
export interface ISessionCachePort {
  set(key: string, value: string, ttlSeconds: number): Promise<void>;
  get(key: string): Promise<string | null>;
}

// 2. Application Layer: Store Session Use Case
export class StoreSessionUseCase {
  constructor(private readonly cache: ISessionCachePort) {}

  async execute(sessionId: string, userId: string): Promise<void> {
    await this.cache.set(`session:${sessionId}`, userId, 3600);
  }
}"""
    },
    {
        "label": "Case 12: Direct Stripe SDK Coupling",
        "category": "HTTP_NETWORK_LEAKAGE",
        "legacy": """import Stripe from 'stripe';

export class SubscriptionManager {
  private stripe = new Stripe('sk_test_123', { apiVersion: '2023-10-16' });

  async cancelCustomerSubscription(subId: string): Promise<void> {
    await this.stripe.subscriptions.cancel(subId);
  }
}""",
        "canonical": """// 1. Application Layer: Subscription Gateway Port
export interface ISubscriptionGatewayPort {
  cancelSubscription(subscriptionId: string): Promise<void>;
}

// 2. Application Layer: Cancel Subscription Use Case
export class CancelSubscriptionUseCase {
  constructor(private readonly gateway: ISubscriptionGatewayPort) {}

  async execute(subscriptionId: string): Promise<void> {
    await this.gateway.cancelSubscription(subscriptionId);
  }
}"""
    },
    {
        "label": "Case 13: Direct AWS S3 Client in Domain",
        "category": "HTTP_NETWORK_LEAKAGE",
        "legacy": """import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

export class AvatarUploader {
  private s3 = new S3Client({});

  async uploadAvatar(userId: string, imageBuffer: Buffer): Promise<void> {
    await this.s3.send(new PutObjectCommand({
      Bucket: 'avatars',
      Key: `${userId}.png`,
      Body: imageBuffer
    }));
  }
}""",
        "canonical": """// 1. Application Layer: File Storage Port Contract
export interface IFileStoragePort {
  upload(destinationPath: string, data: Uint8Array): Promise<string>;
}

// 2. Application Layer: Upload Avatar Use Case
export class UploadAvatarUseCase {
  constructor(private readonly storage: IFileStoragePort) {}

  async execute(userId: string, imageData: Uint8Array): Promise<string> {
    const filePath = `avatars/${userId}.png`;
    return this.storage.upload(filePath, imageData);
  }
}"""
    },
    {
        "label": "Case 14: Direct Twilio Client in SMS Verification",
        "category": "HTTP_NETWORK_LEAKAGE",
        "legacy": """import twilio from 'twilio';

export class SmsVerificationService {
  private client = twilio('AC123', 'token123');

  async sendPin(phoneNumber: string, pin: string): Promise<void> {
    await this.client.messages.create({
      to: phoneNumber,
      from: '+123456789',
      body: `Your verification PIN is: ${pin}`
    });
  }
}""",
        "canonical": """// 1. Application Layer: SMS Dispatcher Port Interface
export interface ISmsDispatcherPort {
  sendSms(phoneNumber: string, message: string): Promise<void>;
}

// 2. Application Layer: Send Verification PIN Use Case
export class SendVerificationPinUseCase {
  constructor(private readonly smsDispatcher: ISmsDispatcherPort) {}

  async execute(phone: string, pin: string): Promise<void> {
    const text = `Your verification PIN is: ${pin}`;
    await this.smsDispatcher.sendSms(phone, text);
  }
}"""
    },

    # --------------------------------------------------------------------------
    # CATEGORY C: PRIMITIVE OBSESSION & UNTYPED THROWS (8 cases)
    # --------------------------------------------------------------------------
    {
        "label": "Case 15: Primitive Obsession on Money & Negative Amounts",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export class BankAccount {
  constructor(public balance: number) {}

  deposit(amount: number): void {
    this.balance += amount;
  }
}""",
        "canonical": """// 1. Domain Layer: Pure Value Object for Money
export class Money {
  private constructor(public readonly amount: number, public readonly currency: string) {}

  public static create(amount: number, currency = 'USD'): Money {
    if (amount < 0) throw new Error('Money amount cannot be negative');
    return new Money(amount, currency);
  }

  public add(other: Money): Money {
    if (this.currency !== other.currency) throw new Error('Currency mismatch');
    return new Money(this.amount + other.amount, this.currency);
  }
}

// 2. Domain Layer: Bank Account Entity
export class BankAccount {
  constructor(public readonly id: string, public readonly balance: Money) {}

  public deposit(amount: Money): BankAccount {
    return new BankAccount(this.id, this.balance.add(amount));
  }
}"""
    },
    {
        "label": "Case 16: Raw String Email with Untyped Generic Throw",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export function registerUser(email: string): { email: string } {
  if (!email.includes('@')) {
    throw new Error('Invalid email');
  }
  return { email };
}""",
        "canonical": r"""// 1. Domain Layer: Email Value Object
export class Email {
  private constructor(public readonly value: string) {}

  public static create(raw: string): Email {
    const trimmed = raw.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      throw new Error('Invalid email format');
    }
    return new Email(trimmed);
  }
}

// 2. Domain Layer: User Registration Result
export interface RegisteredUser {
  readonly email: Email;
}

export function registerUser(rawEmail: string): RegisteredUser {
  const email = Email.create(rawEmail);
  return { email };
}"""
    },
    {
        "label": "Case 17: Password Primitive without Security Invariants",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export class UserCredentials {
  constructor(public username: string, public passwordHash: string) {}

  setPassword(pwd: string): void {
    if (pwd.length < 8) throw new Error('Too short');
    this.passwordHash = pwd;
  }
}""",
        "canonical": """// 1. Domain Layer: Password Value Object
export class Password {
  private constructor(public readonly value: string) {}

  public static create(plain: string): Password {
    if (plain.length < 8) {
      throw new Error('Password must be at least 8 characters long');
    }
    return new Password(plain);
  }
}

// 2. Domain Layer: User Credentials Entity
export class UserCredentials {
  constructor(public readonly username: string, public readonly password: Password) {}
}"""
    },
    {
        "label": "Case 18: Unbounded Order Quantity Primitive",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export class OrderLine {
  constructor(public productId: string, public quantity: number) {}
}""",
        "canonical": """// 1. Domain Layer: Quantity Value Object with Invariants
export class Quantity {
  private constructor(public readonly value: number) {}

  public static create(value: number): Quantity {
    if (!Number.isInteger(value) || value <= 0) {
      throw new Error('Quantity must be a positive integer');
    }
    if (value > 100) {
      throw new Error('Quantity exceeds maximum per-order limit (100)');
    }
    return new Quantity(value);
  }
}

// 2. Domain Layer: Order Line Entity
export class OrderLine {
  constructor(public readonly productId: string, public readonly quantity: Quantity) {}
}"""
    },
    {
        "label": "Case 19: Unbounded Discount Percentage Calculation",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export function calculateDiscount(price: number, discount: number): number {
  return price - (price * discount);
}""",
        "canonical": """// 1. Domain Layer: Percentage Value Object
export class Percentage {
  private constructor(public readonly value: number) {}

  public static create(val: number): Percentage {
    if (val < 0 || val > 100) {
      throw new Error('Percentage must be between 0 and 100');
    }
    return new Percentage(val);
  }

  public applyTo(baseAmount: number): number {
    return baseAmount * (1 - this.value / 100);
  }
}"""
    },
    {
        "label": "Case 20: Inverted Date Range Period Primitives",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export class Booking {
  constructor(public startDate: Date, public endDate: Date) {}
}""",
        "canonical": """// 1. Domain Layer: DateRange Value Object
export class DateRange {
  private constructor(public readonly start: Date, public readonly end: Date) {}

  public static create(start: Date, end: Date): DateRange {
    if (start.getTime() > end.getTime()) {
      throw new Error('Start date must be before or equal to end date');
    }
    return new DateRange(start, end);
  }

  public get durationInDays(): number {
    return Math.ceil((this.end.getTime() - this.start.getTime()) / (1000 * 3600 * 24));
  }
}

// 2. Domain Layer: Pure Booking Entity
export class Booking {
  constructor(public readonly id: string, public readonly period: DateRange) {}
}"""
    },
    {
        "label": "Case 21: Raw Tax Identification Number Primitive",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export class TaxPayer {
  constructor(public taxId: string) {}
}""",
        "canonical": r"""// 1. Domain Layer: TaxId Value Object
export class TaxId {
  private constructor(public readonly value: string) {}

  public static create(raw: string): TaxId {
    const clean = raw.replace(/\D/g, '');
    if (clean.length < 8 || clean.length > 14) {
      throw new Error('Tax identifier must contain between 8 and 14 digits');
    }
    return new TaxId(clean);
  }
}

// 2. Domain Layer: Tax Payer Entity
export class TaxPayer {
  constructor(public readonly id: string, public readonly taxId: TaxId) {}
}"""
    },
    {
        "label": "Case 22: Raw String IP Address Primitive",
        "category": "PRIMITIVE_OBSESSION",
        "legacy": """export class NetworkHost {
  constructor(public hostname: string, public ipAddress: string) {}
}""",
        "canonical": r"""// 1. Domain Layer: IpAddress Value Object
export class IpAddress {
  private constructor(public readonly value: string) {}

  public static create(raw: string): IpAddress {
    const ipv4Regex = /^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$/;
    if (!ipv4Regex.test(raw)) {
      throw new Error('Invalid IPv4 address format');
    }
    return new IpAddress(raw);
  }
}

// 2. Domain Layer: Network Host Entity
export class NetworkHost {
  constructor(public readonly hostname: string, public readonly ip: IpAddress) {}
}"""
    },

    # --------------------------------------------------------------------------
    # CATEGORY D: TYPESCRIPT ANY-TYPE PROLIFERATION & LACK OF CONTRACTS (5 cases)
    # --------------------------------------------------------------------------
    {
        "label": "Case 23: Untyped Any Payment Payload",
        "category": "ANY_TYPE_PROLIFERATION",
        "legacy": """export function processPayment(payload: any): any {
  return {
    status: 'SUCCESS',
    refId: payload.id,
    charged: payload.amount
  };
}""",
        "canonical": """// 1. Application Layer: Strict Input DTO
export interface PaymentRequestDTO {
  readonly id: string;
  readonly amount: number;
}

// 2. Application Layer: Strict Output DTO
export interface PaymentResponseDTO {
  readonly status: 'SUCCESS' | 'FAILED';
  readonly refId: string;
  readonly charged: number;
}

// 3. Application Layer: Type-Safe Function
export function processPayment(payload: PaymentRequestDTO): PaymentResponseDTO {
  return {
    status: 'SUCCESS',
    refId: payload.id,
    charged: payload.amount
  };
}"""
    },
    {
        "label": "Case 24: Untyped Webhook Event Handler",
        "category": "ANY_TYPE_PROLIFERATION",
        "legacy": """export function handleWebhook(event: any): any {
  const type = event.type;
  const data = event.data;
  return { processed: true, type, id: data.id };
}""",
        "canonical": """// 1. Application Layer: Strongly Typed Webhook Contract
export interface WebhookEvent<T = Record<string, unknown>> {
  readonly id: string;
  readonly type: string;
  readonly data: T;
}

export interface WebhookResult {
  readonly processed: boolean;
  readonly type: string;
  readonly id: string;
}

export function handleWebhook<T extends { id: string }>(event: WebhookEvent<T>): WebhookResult {
  return {
    processed: true,
    type: event.type,
    id: event.data.id
  };
}"""
    },
    {
        "label": "Case 25: Untyped Order Item Calculation",
        "category": "ANY_TYPE_PROLIFERATION",
        "legacy": """export function computeTotal(items: any[]): number {
  return items.reduce((acc: any, item: any) => acc + (item.price * item.qty), 0);
}""",
        "canonical": """// 1. Domain Layer: Order Item Contract
export interface OrderItem {
  readonly price: number;
  readonly quantity: number;
}

export function computeTotal(items: readonly OrderItem[]): number {
  return items.reduce((acc, item) => acc + (item.price * item.quantity), 0);
}"""
    },
    {
        "label": "Case 26: Loose Untyped User Profile Metadata",
        "category": "ANY_TYPE_PROLIFERATION",
        "legacy": """export class UserProfile {
  constructor(public id: string, public metadata: any) {}
}""",
        "canonical": """// 1. Domain Layer: Strongly Typed Metadata Contract
export interface UserProfileMetadata {
  readonly bio?: string;
  readonly avatarUrl?: string;
  readonly preferredLanguage: string;
  readonly notificationsEnabled: boolean;
}

export class UserProfile {
  constructor(
    public readonly id: string,
    public readonly metadata: UserProfileMetadata
  ) {}
}"""
    },
    {
        "label": "Case 27: Untyped Batch Importer",
        "category": "ANY_TYPE_PROLIFERATION",
        "legacy": """export class BatchImporter {
  importData(records: any[]): any {
    return records.map((r: any) => ({ key: r.id, value: r.name }));
  }
}""",
        "canonical": """// 1. Application Layer: Generic Type-Safe DTOs
export interface RawRecord {
  readonly id: string;
  readonly name: string;
}

export interface NormalizedRecord {
  readonly key: string;
  readonly value: string;
}

export class BatchImporter {
  importData(records: readonly RawRecord[]): readonly NormalizedRecord[] {
    return records.map((r) => ({ key: r.id, value: r.name }));
  }
}"""
    },

    # --------------------------------------------------------------------------
    # CATEGORY E: MONOLITHIC GOD CLASSES (3 cases)
    # --------------------------------------------------------------------------
    {
        "label": "Case 28: Monolithic Checkout Controller (Multi-Antipattern)",
        "category": "GOD_CLASS_MONOLITH",
        "legacy": """import express from 'express';
import { Client } from 'pg';
import axios from 'axios';

export class CheckoutController {
  async handle(req: express.Request, res: express.Response): Promise<void> {
    const { userId, cartItems, cardToken } = req.body;
    let total = 0;
    for (const item of cartItems) {
      total += item.price * item.quantity;
    }
    const chargeRes = await axios.post('https://stripe.com/charge', { token: cardToken, amount: total });
    const pgClient = new Client();
    await pgClient.connect();
    await pgClient.query('INSERT INTO orders (user_id, total) VALUES ($1, $2)', [userId, total]);
    res.json({ success: true, chargeId: chargeRes.data.id });
  }
}""",
        "canonical": """// 1. Domain Layer: Pure Order Entity
export class Order {
  constructor(public readonly userId: string, public readonly total: number) {}
}

// 2. Application Layer: Ports
export interface IPaymentPort {
  charge(token: string, amount: number): Promise<string>;
}

export interface IOrderRepoPort {
  save(order: Order): Promise<void>;
}

// 3. Application Layer: Checkout Use Case
export class CheckoutUseCase {
  constructor(
    private readonly paymentPort: IPaymentPort,
    private readonly orderRepo: IOrderRepoPort
  ) {}

  async execute(userId: string, total: number, cardToken: string): Promise<string> {
    const chargeId = await this.paymentPort.charge(cardToken, total);
    const order = new Order(userId, total);
    await this.orderRepo.save(order);
    return chargeId;
  }
}"""
    },
    {
        "label": "Case 29: Monolithic User Registration Manager",
        "category": "GOD_CLASS_MONOLITH",
        "legacy": """import { PrismaClient } from '@prisma/client';
import axios from 'axios';

export class UserManager {
  private prisma = new PrismaClient();

  async register(reqBody: any): Promise<any> {
    if (!reqBody.email || !reqBody.password) throw new Error('Missing fields');
    const user = await this.prisma.user.create({ data: reqBody });
    await axios.post('https://analytics.service.com/event', { event: 'SIGNUP', userId: user.id });
    return user;
  }
}""",
        "canonical": """// 1. Domain Layer: User Entity
export class User {
  constructor(public readonly id: string, public readonly email: string) {}
}

// 2. Application Layer: Ports
export interface IUserRepositoryPort {
  create(email: string): Promise<User>;
}

export interface IAnalyticsPort {
  track(event: string, userId: string): Promise<void>;
}

// 3. Application Layer: Register User Use Case
export class RegisterUserUseCase {
  constructor(
    private readonly userRepo: IUserRepositoryPort,
    private readonly analytics: IAnalyticsPort
  ) {}

  async execute(email: string): Promise<User> {
    const user = await this.userRepo.create(email);
    await this.analytics.track('SIGNUP', user.id);
    return user;
  }
}"""
    },
    {
        "label": "Case 30: Monolithic Invoice & PDF Dispatcher",
        "category": "GOD_CLASS_MONOLITH",
        "legacy": """import { Client } from 'pg';
import axios from 'axios';
import fs from 'fs';

export class InvoiceDispatcher {
  async process(invoiceId: string): Promise<void> {
    const client = new Client();
    await client.connect();
    const res = await client.query('SELECT * FROM invoices WHERE id = $1', [invoiceId]);
    fs.writeFileSync('/tmp/invoice.txt', JSON.stringify(res.rows[0]));
    await axios.post('https://mailer.internal.net/send', { file: '/tmp/invoice.txt' });
  }
}""",
        "canonical": """// 1. Domain Layer: Invoice Entity
export class Invoice {
  constructor(public readonly id: string, public readonly total: number) {}
}

// 2. Application Layer: Ports
export interface IInvoicePort {
  findById(id: string): Promise<Invoice | null>;
}

export interface IInvoiceDeliveryPort {
  deliver(invoice: Invoice): Promise<void>;
}

// 3. Application Layer: Dispatch Invoice Use Case
export class DispatchInvoiceUseCase {
  constructor(
    private readonly invoiceRepo: IInvoicePort,
    private readonly delivery: IInvoiceDeliveryPort
  ) {}

  async execute(invoiceId: string): Promise<void> {
    const invoice = await this.invoiceRepo.findById(invoiceId);
    if (!invoice) throw new Error('Invoice not found');
    await this.delivery.deliver(invoice);
  }
}"""
    }
]

def main():
    print(f"--> Generating {len(CASES)} Legacy Benchmark Test Cases...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for idx, item in enumerate(CASES, start=1):
            chatml_entry = {
                "label": item["label"],
                "category": item["category"],
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Refactor the following legacy TypeScript code to adhere strictly to Clean Architecture "
                            f"and Ports & Adapters. Eliminate framework coupling, encapsulate invariants, and use explicit typing:\n\n"
                            f"```typescript\n{item['legacy']}\n```"
                        )
                    },
                    {
                        "role": "assistant",
                        "content": (
                            f"```typescript\n{item['canonical']}\n```"
                        )
                    }
                ]
            }
            f.write(json.dumps(chatml_entry, ensure_ascii=False) + "\n")

    print(f"[OK] Successfully wrote {len(CASES)} cases to {OUTPUT_FILE.resolve()}")

if __name__ == "__main__":
    main()
