import { SchemaAnalysis } from '../types';

export interface SchemaOptions {
  type: 'Article' | 'BlogPosting' | 'Product' | 'LocalBusiness' | 'Organization' | 'WebSite' | 'FAQPage' | 'Course' | 'Recipe' | 'VideoObject' | 'Person' | 'Event' | 'Service';
  name: string;
  description: string;
  url: string;
  image?: string;
  author?: string;
  publishedDate?: string;
  modifiedDate?: string;
  price?: string;
  currency?: string;
  availability?: 'InStock' | 'OutOfStock' | 'PreOrder';
  brand?: string;
  sku?: string;
  address?: {
    street: string;
    city: string;
    region: string;
    postalCode: string;
    country: string;
  };
  phone?: string;
  priceRange?: string;
  rating?: number;
  reviewCount?: number;
  questions?: { question: string; answer: string }[];
  courseDetails?: {
    provider: string;
    offers: { price: string; currency: string };
    hasCourseInstance: string[];
  };
  recipeDetails?: {
    prepTime: string;
    cookTime: string;
    totalTime: string;
    recipeYield: string;
    ingredients: string[];
    instructions: string[];
  };
}

export class SchemaGenerator {
  generate(options: SchemaOptions): string {
    const baseSchema = this.getBaseSchema(options);
    const specificSchema = this.getTypeSpecificSchema(options);

    return JSON.stringify({ ...baseSchema, ...specificSchema }, null, 2);
  }

  private getBaseSchema(options: SchemaOptions) {
    const schema: any = {
      '@context': 'https://schema.org',
      '@type': options.type,
      name: options.name,
      description: options.description,
      url: options.url
    };

    if (options.image) {
      schema.image = options.image;
    }

    if (options.author) {
      schema.author = { '@type': 'Person', name: options.author };
    }

    if (options.publishedDate) {
      schema.datePublished = options.publishedDate;
    }

    if (options.modifiedDate) {
      schema.dateModified = options.modifiedDate;
    }

    return schema;
  }

  private getTypeSpecificSchema(options: SchemaOptions) {
    switch (options.type) {
      case 'Article':
      case 'BlogPosting':
        return {
          headline: options.name,
          articleSection: 'SEO',
          wordCount: options.description.split(' ').length
        };

      case 'Product':
        return {
          offers: {
            '@type': 'Offer',
            price: options.price || '0',
            priceCurrency: options.currency || 'USD',
            availability: options.availability ? `https://schema.org/${options.availability}` : 'https://schema.org/InStock'
          },
          brand: options.brand ? { '@type': 'Brand', name: options.brand } : undefined,
          sku: options.sku
        };

      case 'LocalBusiness':
        const address: any = {};
        if (options.address) {
          address['@type'] = 'PostalAddress';
          address.streetAddress = options.address.street;
          address.addressLocality = options.address.city;
          address.addressRegion = options.address.region;
          address.postalCode = options.address.postalCode;
          address.addressCountry = options.address.country;
        }

        return {
          address,
          telephone: options.phone,
          priceRange: options.priceRange,
          ...(options.rating && {
            aggregateRating: {
              '@type': 'AggregateRating',
              ratingValue: options.rating,
              reviewCount: options.reviewCount || 0
            }
          })
        };

      case 'Organization':
        return {
          logo: options.image,
          contactPoint: options.phone ? { '@type': 'ContactPoint', telephone: options.phone } : undefined
        };

      case 'FAQPage':
        return {
          mainEntity: (options.questions || []).map(q => ({
            '@type': 'Question',
            name: q.question,
            acceptedAnswer: {
              '@type': 'Answer',
              text: q.answer
            }
          }))
        };

      case 'Course':
        return {
          provider: {
            '@type': 'Organization',
            name: options.courseDetails?.provider || 'SEO Engine'
          },
          offers: options.courseDetails?.offers ? {
            '@type': 'Offer',
            price: options.courseDetails.offers.price,
            priceCurrency: options.courseDetails.offers.currency
          } : undefined,
          hasCourseInstance: options.courseDetails?.hasCourseInstance?.map(i => ({
            '@type': 'CourseInstance',
            courseMode: i
          }))
        };

      case 'Recipe':
        return {
          prepTime: options.recipeDetails?.prepTime,
          cookTime: options.recipeDetails?.cookTime,
          totalTime: options.recipeDetails?.totalTime,
          recipeYield: options.recipeDetails?.recipeYield,
          recipeIngredient: options.recipeDetails?.ingredients || [],
          recipeInstructions: options.recipeDetails?.instructions?.map(i => ({
            '@type': 'HowToStep',
            text: i
          }))
        };

      case 'VideoObject':
        return {
          duration: 'PT0M0S',
          uploadDate: options.publishedDate
        };

      case 'Event':
        return {
          eventStatus: 'https://schema.org/EventScheduled',
          eventAttendanceMode: 'https://schema.org/OnlineEventAttendanceMode'
        };

      case 'Service':
        return {
          provider: {
            '@type': 'Organization',
            name: options.author || 'SEO Engine'
          },
          areaServed: 'Worldwide',
          serviceType: options.name
        };

      default:
        return {};
    }
  }

  detectMissingSchema(html: string): string[] {
    const missing: string[] = [];
    const $ = cheerio.load(html);

    if (!$('script[type="application/ld+json"]').length) {
      missing.push('No JSON-LD schema found');
    }

    if (!$('[itemtype*="schema.org"]').length) {
      missing.push('No Microdata found');
    }

    return missing;
  }

  validateSchema(jsonLd: string): { valid: boolean; errors: string[] } {
    try {
      const parsed = JSON.parse(jsonLd);

      if (!parsed['@context'] || !parsed['@context'].includes('schema.org')) {
        return { valid: false, errors: ['Missing or invalid @context'] };
      }

      if (!parsed['@type']) {
        return { valid: false, errors: ['Missing @type'] };
      }

      return { valid: true, errors: [] };
    } catch (error) {
      return { valid: false, errors: ['Invalid JSON syntax'] };
    }
  }

  generateBreadcrumb(items: { name: string; url: string }[]): string {
    const schema = {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: items.map((item, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: item.name,
        item: item.url
      }))
    };

    return JSON.stringify(schema, null, 2);
  }

  generateOrganization(organization: {
    name: string;
    url: string;
    logo?: string;
    description?: string;
    sameAs?: string[];
    contactEmail?: string;
    contactPhone?: string;
    address?: {
      street: string;
      city: string;
      country: string;
    };
  }): string {
    const schema = {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: organization.name,
      url: organization.url,
      ...(organization.logo && { logo: organization.logo }),
      ...(organization.description && { description: organization.description }),
      ...(organization.sameAs && { sameAs: organization.sameAs }),
      ...(organization.contactEmail && {
        contactPoint: {
          '@type': 'ContactPoint',
          email: organization.contactEmail,
          contactType: 'customer service',
          ...(organization.contactPhone && { telephone: organization.contactPhone })
        }
      }),
      ...(organization.address && {
        address: {
          '@type': 'PostalAddress',
          streetAddress: organization.address.street,
          addressLocality: organization.address.city,
          addressCountry: organization.address.country
        }
      })
    };

    return JSON.stringify(schema, null, 2);
  }
}

import * as cheerio from 'cheerio';

export default SchemaGenerator;