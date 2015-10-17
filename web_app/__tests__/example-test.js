// __tests__/example-test.js
jest.dontMock('../example');

describe('example', function () {
    it('give the test descript', function () {
        expect(example().toBe());
    });
});
