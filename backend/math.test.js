const { add, subtract, multiply, divide } = require('./math');

describe('Math functions', () => {
    test('adds 1 + 2 to equal 3', () => {
        expect(add(1, 2)).toBe(3);
    });

    test('adds -1 + 5 to equal 4', () => {
        expect(add(-1, 5)).toBe(4);
    });

    test('subtracts 5 - 3 to equal 2', () => {
        expect(subtract(5, 3)).toBe(2);
    });

    test('subtracts 10 - 15 to equal -5', () => {
        expect(subtract(10, 15)).toBe(-5);
    });

    test('multiplies 3 * 4 to equal 12', () => {
        expect(multiply(3, 4)).toBe(12);
    });

    test('multiplies -2 * 6 to equal -12', () => {
        expect(multiply(-2, 6)).toBe(-12);
    });

    test('divides 10 / 2 to equal 5', () => {
        expect(divide(10, 2)).toBe(5);
    });

    test('divides 7 / 2 to equal 3.5', () => {
        expect(divide(7, 2)).toBe(3.5);
    });

    test('throws error when dividing by zero', () => {
        expect(() => divide(10, 0)).toThrow('Division by zero');
    });
});